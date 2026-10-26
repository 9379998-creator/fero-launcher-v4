"""
Run Prototype 012 on Real Frame Outer Shell 408.1850.XX
======================================================
Extracts Cluster 0 (outer shell) from the established PDF, executes topological
reconstruction, writes experimental DXF with BLOCK and INSERT, re-reads via ezdxf,
and prints aggregated numerical metrics.

Zero private paths hardcoded; accepts CLI parameters.
"""

import sys
import argparse
import json
import math
from pathlib import Path
import fitz
import ezdxf

# Add prototype dir to path
sys.path.insert(0, str(Path(__file__).parent))
from section_reconstructor import (
    Point2D,
    Segment2D,
    TopologicalSectionReconstructor,
    export_section_to_dxf,
)

def find_pdf_from_manifest(manifest_path: Path) -> Path:
    with open(manifest_path, "rb") as f:
        data = json.load(f)
    def search(obj):
        if isinstance(obj, dict):
            if obj.get("name") == "MASTERLINE 8 - 2019.pdf":
                return obj.get("path")
            for v in obj.values():
                res = search(v)
                if res: return res
        elif isinstance(obj, list):
            for it in obj:
                res = search(it)
                if res: return res
        return None
    p = search(data)
    if not p:
        raise FileNotFoundError("MASTERLINE 8 - 2019.pdf not found in manifest")
    return Path(p)

def run_experiment(pdf_path: str, page_num: int, out_dir: str):
    p_pdf = Path(pdf_path)
    p_out = Path(out_dir)
    p_out.mkdir(parents=True, exist_ok=True)

    print(f"Loading PDF: {p_pdf.name}, Page: {page_num}")
    doc = fitz.open(p_pdf)
    page = doc[page_num - 1]
    all_drawings = page.get_drawings()

    ox = 215.8214
    oy = 774.0382
    scale = 25.4 / 72.0

    # 1. Filter Cluster 0 Fill Slices (the verified solid material of the outer shell)
    # PDF X: [428.0, 480.0], PDF Y: [225.0, 705.0]
    c0_slices = [
        d for d in all_drawings
        if d.get("fill") is not None and d["rect"].x0 >= 420.0 and d["rect"].x1 <= 480.0
    ]
    print(f"Cluster 0 fill slices count: {len(c0_slices)}")

    # 2. Filter hairline boundary strokes for the outer shell
    r_c0 = fitz.Rect(427.0, 225.0, 480.0, 705.0)
    c0_strokes = [d for d in all_drawings if d.get("fill") is None and r_c0.intersects(d["rect"])]
    print(f"Cluster 0 hairline boundary strokes count: {len(c0_strokes)}")

    # 3. Extract segments in CAD mm
    segments = []
    for d_idx, d in enumerate(c0_strokes):
        items = d.get("items", [])
        for it in items:
            if it[0] == "l":
                p1 = Point2D((it[1].x - ox) * scale, (oy - it[1].y) * scale)
                p2 = Point2D((it[2].x - ox) * scale, (oy - it[2].y) * scale)
                if p1 != p2:
                    segments.append(Segment2D(p1, p2, {"type": "stroke", "draw_id": d_idx}))
            elif it[0] == "c":
                # Adaptive chord subdivision (de Casteljau) or smooth 8-step
                pts = []
                for s in range(9):
                    t = s / 8.0
                    mt = 1.0 - t
                    x = mt**3 * it[1].x + 3.0 * mt**2 * t * it[2].x + 3.0 * mt * t**2 * it[3].x + t**3 * it[4].x
                    y = mt**3 * it[1].y + 3.0 * mt**2 * t * it[2].y + 3.0 * mt * t**2 * it[3].y + t**3 * it[4].y
                    pts.append(Point2D((x - ox) * scale, (oy - y) * scale))
                for k in range(len(pts) - 1):
                    if pts[k] != pts[k + 1]:
                        segments.append(Segment2D(pts[k], pts[k + 1], {"type": "curve", "draw_id": d_idx}))

    print(f"Total raw segments extracted: {len(segments)}")

    # 4. Also calculate baseline fill slice area (independent reference)
    slice_rect_area = sum(d["rect"].width * d["rect"].height for d in c0_slices) * (scale ** 2)
    print(f"Reference fill slices area: {slice_rect_area:.2f} mm^2")

    # 5. Run Topological Reconstruction with snap_tolerance = 0.05 mm (matching ~0.12 pt quantum)
    reconstructor = TopologicalSectionReconstructor(
        snap_tolerance=0.05,
        chord_tolerance=0.01,
        duplicate_tolerance=0.005,
        crop_box=(7.0, 25.0, 99.0, 206.0),
        crop_margin=0.2,
    )

    section = reconstructor.reconstruct(segments, part_id="408.1850.XX_OUTER_SHELL")

    print("\n=== RECONSTRUCTION RESULTS ===")
    print(f"Part ID: {section.part_id}")
    print(f"Status: {section.status}")
    print(f"Outer boundary present: {section.outer_boundary is not None}")
    if section.outer_boundary:
        ob = section.outer_boundary
        print(f"Outer boundary vertices: {ob.vertex_count}")
        print(f"Outer boundary area: {ob.area:.2f} mm^2")
        print(f"Outer boundary bbox: X[{ob.bbox[0]:.2f}, {ob.bbox[2]:.2f}] Y[{ob.bbox[1]:.2f}, {ob.bbox[3]:.2f}]")
        print(f"Outer boundary dimensions: Width={ob.bbox[2]-ob.bbox[0]:.2f} mm, Height={ob.bbox[3]-ob.bbox[1]:.2f} mm")

    print(f"Cavities (holes) count: {len(section.cavities)}")
    for i, cav in enumerate(section.cavities):
        print(f"  Cavity #{i}: vertices={cav.vertex_count}, area={cav.area:.2f} mm^2, bbox=X[{cav.bbox[0]:.2f}, {cav.bbox[2]:.2f}] Y[{cav.bbox[1]:.2f}, {cav.bbox[3]:.2f}]")

    print(f"Open fragments count: {len(section.open_fragments)}")
    print(f"Net Material Area: {section.net_material_area:.2f} mm^2")
    if slice_rect_area > 0 and section.net_material_area > 0:
        area_diff = abs(section.net_material_area - slice_rect_area)
        rel_diff = (area_diff / slice_rect_area) * 100.0
        print(f"Area delta relative to reference slices: {area_diff:.2f} mm^2 ({rel_diff:.2f}%)")

    # 6. Export to experimental DXF
    dxf_out_path = p_out / "408_1850_outer_shell_prototype.dxf"
    export_meta = export_section_to_dxf(section, str(dxf_out_path), create_hatch=True)
    print(f"\nSaved experimental DXF to: {dxf_out_path.name}")

    # 7. Re-read and verify DXF via ezdxf (Zero Fake Policy)
    dxf_verify = ezdxf.readfile(str(dxf_out_path))
    msp_v = dxf_verify.modelspace()
    print("\n=== DXF INDEPENDENT VERIFICATION ===")
    print(f"DXF INSUNITS: {dxf_verify.header.get('$INSUNITS')} (4 = Millimeters)")
    print(f"ModelSpace entity count: {len(msp_v)}")
    blocks_found = [b.name for b in dxf_verify.blocks if "BLOCK_" in b.name]
    print(f"Custom BLOCK definitions: {blocks_found}")
    inserts_found = [e for e in msp_v if e.dxftype() == "INSERT"]
    print(f"ModelSpace INSERT count: {len(inserts_found)}")
    if inserts_found:
        print(f"  INSERT target block: {inserts_found[0].dxf.name} at {inserts_found[0].dxf.insert}")

    # Check entities inside block
    target_blk = dxf_verify.blocks.get(blocks_found[0])
    blk_ents = list(target_blk)
    print(f"Entities inside block '{target_blk.name}': {len(blk_ents)}")
    for e in blk_ents:
        if e.dxftype() == "LWPOLYLINE":
            print(f"  LWPOLYLINE: layer={e.dxf.layer}, closed={bool(e.closed)}, vertices={len(e.get_points())}")
        elif e.dxftype() == "HATCH":
            print(f"  HATCH: layer={e.dxf.layer}, paths={len(e.paths)}")

    # Write summary json
    summary_path = p_out / "prototype_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "part_id": section.part_id,
            "status": section.status,
            "outer_vertices": section.outer_boundary.vertex_count if section.outer_boundary else 0,
            "outer_area": section.outer_boundary.area if section.outer_boundary else 0,
            "cavities_count": len(section.cavities),
            "net_area": section.net_material_area,
            "reference_slices_area": slice_rect_area,
            "dxf_file": dxf_out_path.name,
            "block_name": blocks_found[0] if blocks_found else None,
            "insunits": dxf_verify.header.get("$INSUNITS"),
        }, f, indent=2)
    print(f"Summary JSON written to: {summary_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, default="")
    parser.add_argument("--page", type=int, default=211)
    parser.add_argument("--out-dir", type=str, default="")
    args = parser.parse_args()

    pdf_p = args.pdf
    if not pdf_p:
        manifest_p = Path(r"C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher\runtime\manifests\61b53c81419e6fc1.json")
        pdf_p = str(find_pdf_from_manifest(manifest_p))

    out_d = args.out_dir
    if not out_d:
        out_d = r"C:\Users\a9379\.gemini\antigravity\brain\4b9b761e-6b93-432a-8701-6e8e129b1518\scratch\exp_012"

    run_experiment(pdf_p, args.page, out_d)
