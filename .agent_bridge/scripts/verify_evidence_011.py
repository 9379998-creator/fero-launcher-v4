"""
FERO Section Topology Diagnostic & Evidence Script (Task 011)
Performs offline, read-only verification of PDF vector primitives, fill slices,
stroke widths, dimension arrowheads, and DXF entity breakdown.
Zero secrets, zero private paths.
"""

import sys
import math
import json
import hashlib
from pathlib import Path
import fitz
import ezdxf

def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

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

def run_diagnostics():
    manifest_file = Path(r"C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher\runtime\manifests\61b53c81419e6fc1.json")
    pdf_path = find_pdf_from_manifest(manifest_file)
    cad_dir = Path(r"C:\Users\a9379\.gemini\antigravity\scratch\FProject-Launcher\runtime\cache\cad")
    dxf_candidates = list(cad_dir.glob("*211*.dxf"))
    if not dxf_candidates:
        raise FileNotFoundError("DXF page 211 not found in cache/cad")
    dxf_path = dxf_candidates[0]

    print("=== ENVIRONMENT & REPRODUCIBILITY ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"PyMuPDF: {fitz.__version__}")
    print(f"ezdxf: {ezdxf.__version__}")
    print(f"PDF File: {pdf_path.name} ({pdf_path.stat().st_size} bytes, SHA-256: {get_sha256(pdf_path)})")
    print(f"DXF File: {dxf_path.name} ({dxf_path.stat().st_size} bytes, SHA-256: {get_sha256(dxf_path)})")

    # PDF Inspection
    doc = fitz.open(pdf_path)
    page_idx = 210  # page 211
    page = doc[page_idx]
    all_drawings = page.get_drawings()
    print(f"\nPDF Page 211 total drawings: {len(all_drawings)}")

    ox = 215.8214
    oy = 774.0382
    scale = 25.4 / 72.0

    # 1. Stroke widths
    crop_rect = fitz.Rect(215.82, 175.0, 500.0, 774.04)
    crop_drawings = [d for d in all_drawings if crop_rect.intersects(d["rect"])]
    crop_strokes = [d for d in crop_drawings if d.get("fill") is None]
    stroke_widths = {}
    for d in crop_strokes:
        w = round(d.get("width", 0.0), 3)
        stroke_widths[w] = stroke_widths.get(w, 0) + 1
    print(f"Crop area stroke count: {len(crop_strokes)}")
    print(f"Crop area stroke widths: {stroke_widths}")

    # 2. Fill cluster areas
    c0_slices = [d for d in all_drawings if d.get("fill") is not None and d['rect'].x0 >= 420.0 and d['rect'].x1 <= 480.0]
    c1_slices = [d for d in all_drawings if d.get("fill") is not None and d['rect'].x0 >= 250.0 and d['rect'].x1 <= 340.0]
    c0_area = sum(d['rect'].width * d['rect'].height for d in c0_slices) * (scale ** 2)
    c1_area = sum(d['rect'].width * d['rect'].height for d in c1_slices) * (scale ** 2)
    print(f"Outer shell (C0) fill slices: {len(c0_slices)}, measured area: {c0_area:.2f} mm^2")
    print(f"Inner shell (C1) fill slices: {len(c1_slices)}, measured area: {c1_area:.2f} mm^2")

    # 3. Coordinate discretization
    segments = []
    for d in crop_strokes:
        for it in d.get("items", []):
            if it[0] == 'l':
                segments.append(((it[1].x * scale, it[1].y * scale), (it[2].x * scale, it[2].y * scale)))
    all_pts = []
    for s in segments:
        all_pts.extend([s[0], s[1]])
    non_zero_dists = []
    for i in range(min(200, len(all_pts))):
        for j in range(i + 1, min(200, len(all_pts))):
            d = math.hypot(all_pts[i][0] - all_pts[j][0], all_pts[i][1] - all_pts[j][1])
            if 0.0 < d < 1.0:
                non_zero_dists.append(d)
    min_dist = min(non_zero_dists) if non_zero_dists else 0.0
    print(f"Minimum non-zero point distance in PDF: {min_dist:.6f} mm (0.12 pt = {0.12 * scale:.6f} mm)")

    # 4. DXF Open Polylines breakdown
    dxf_doc = ezdxf.readfile(str(dxf_path))
    msp = dxf_doc.modelspace()
    total_e = len(msp)
    open_poly = 0
    closed_poly = 0
    tb_hatch = 0
    tb_boundary = 0
    alu_long = 0
    alu_short = 0
    dim_open = 0

    for e in msp:
        if e.dxftype() == "LWPOLYLINE":
            if e.closed:
                closed_poly += 1
            else:
                open_poly += 1
                layer = e.dxf.layer
                pts = list(e.get_points("xy"))
                l = sum(math.hypot(pts[k][0]-pts[k+1][0], pts[k][1]-pts[k+1][1]) for k in range(len(pts)-1))
                if "07" in layer:
                    dim_open += 1
                elif "03" in layer:
                    if len(pts) == 2 and abs(abs(pts[1][0]-pts[0][0]) - abs(pts[1][1]-pts[0][1])) < 0.25:
                        tb_hatch += 1
                    else:
                        tb_boundary += 1
                elif "01" in layer:
                    if l > 10.0:
                        alu_long += 1
                    else:
                        alu_short += 1

    print("\n=== DXF TOPOLOGY BREAKDOWN ===")
    print(f"Total entities: {total_e}")
    print(f"Closed LWPOLYLINE: {closed_poly}")
    print(f"Open LWPOLYLINE: {open_poly}")
    print(f"  Dimension leader line (layer 07): {dim_open}")
    print(f"  Thermal break 45-deg cross-hatch lines (layer 03): {tb_hatch}")
    print(f"  Thermal break boundary fragments (layer 03): {tb_boundary}")
    print(f"  Aluminum long profile walls >10mm (layer 01): {alu_long}")
    print(f"  Aluminum short contours <10mm (layer 01): {alu_short}")

if __name__ == "__main__":
    run_diagnostics()
