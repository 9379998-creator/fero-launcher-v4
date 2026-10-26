"""
FERO Architectural CAD Section Reconstructor - Prototype 012
=============================================================
Autonomous, clean-room 2D topological reconstructor for single architectural
profile sections (shells and thermal breaks).

Features:
- Parameterized input (no hardcoded private paths).
- Graph-based path chaining with controlled snapping tolerance.
- Ambiguity detection: logs branching conflicts instead of blind nearest-neighbor snapping.
- Preserves thin features (no destructive bbox/area thresholds).
- Proper loop hierarchy classification: outer boundary vs. internal cavity holes
  via winding number / ray casting.
- Crop-edge boundary detection: marks clipped parts as incomplete (no artificial sealing).
- CAD output: writes clean DXF R2013 with AutoCAD BLOCK and INSERT entities,
  proper layer assignment, and mm units ($INSUNITS = 4).
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any, Set
from collections import defaultdict
import ezdxf
from ezdxf.enums import TextEntityAlignment


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def dist_to(self, other: "Point2D") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def round(self, ndigits: int = 4) -> "Point2D":
        return Point2D(round(self.x, ndigits), round(self.y, ndigits))


@dataclass
class Segment2D:
    p1: Point2D
    p2: Point2D
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> float:
        return self.p1.dist_to(self.p2)

    def reversed(self) -> "Segment2D":
        return Segment2D(self.p2, self.p1, dict(self.meta))


def polygon_shoelace_area(pts: List[Point2D]) -> float:
    """Signed Shoelace area. Positive for CCW, negative for CW."""
    if len(pts) < 3:
        return 0.0
    area = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        area += pts[i].x * pts[j].y
        area -= pts[j].x * pts[i].y
    return area / 2.0


def point_in_polygon(pt: Point2D, poly: List[Point2D]) -> bool:
    """Standard ray-casting test. Returns True if pt is strictly inside poly."""
    inside = False
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        p_i, p_j = poly[i], poly[j]
        # Check ray to the right (+X)
        if ((p_i.y > pt.y) != (p_j.y > pt.y)) and (
            pt.x < (p_j.x - p_i.x) * (pt.y - p_i.y) / (p_j.y - p_i.y + 1e-12) + p_i.x
        ):
            inside = not inside
    return inside


@dataclass
class ReconstructedLoop:
    points: List[Point2D]
    is_closed: bool
    is_outer: bool
    area: float
    is_incomplete: bool = False
    ambiguities: List[str] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return len(self.points)

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        if not self.points:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class ReconstructedSection:
    part_id: str
    outer_boundary: Optional[ReconstructedLoop]
    cavities: List[ReconstructedLoop] = field(default_factory=list)
    open_fragments: List[ReconstructedLoop] = field(default_factory=list)
    net_material_area: float = 0.0
    status: str = "ok"  # "ok", "incomplete", "ambiguous", "failed"
    log_messages: List[str] = field(default_factory=list)


class TopologicalSectionReconstructor:
    """
    Constructs clean outer boundaries and cavity loops from vector segments.
    """

    def __init__(
        self,
        snap_tolerance: float = 0.05,
        chord_tolerance: float = 0.01,
        duplicate_tolerance: float = 0.005,
        crop_box: Optional[Tuple[float, float, float, float]] = None,
        crop_margin: float = 0.2,
    ):
        self.snap_tol = snap_tolerance
        self.chord_tol = chord_tolerance
        self.dup_tol = duplicate_tolerance
        self.crop_box = crop_box
        self.crop_margin = crop_margin

    def is_near_crop(self, pt: Point2D) -> bool:
        if not self.crop_box:
            return False
        x0, y0, x1, y1 = self.crop_box
        m = self.crop_margin
        return (
            abs(pt.x - x0) <= m
            or abs(pt.x - x1) <= m
            or abs(pt.y - y0) <= m
            or abs(pt.y - y1) <= m
        )

    def deduplicate_segments(self, segments: List[Segment2D]) -> List[Segment2D]:
        """
        Deduplicate segments:
        - If an edge appears twice in the same direction, keep 1 copy.
        - If an edge appears in opposite directions (e.g. shared interface between
          abutting scanline fill slices), cancel both copies to expose outer boundary.
        """
        counts: Dict[Tuple[Tuple[float, float], Tuple[float, float]], int] = defaultdict(int)
        seg_map: Dict[Tuple[Tuple[float, float], Tuple[float, float]], Segment2D] = {}

        for seg in segments:
            p1_t = (round(seg.p1.x, 4), round(seg.p1.y, 4))
            p2_t = (round(seg.p2.x, 4), round(seg.p2.y, 4))
            if p1_t == p2_t:
                continue
            key = (p1_t, p2_t)
            counts[key] += 1
            seg_map[key] = seg

        unique: List[Segment2D] = []
        processed: Set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()

        for key, cnt in counts.items():
            if key in processed:
                continue
            rev_key = (key[1], key[0])
            rev_cnt = counts.get(rev_key, 0)

            if rev_cnt > 0:
                # Opposite directed edges exist (interface between abutting regions)
                # Net flux: if counts differ, keep the net difference; if equal, cancel out.
                net = cnt - rev_cnt
                if net > 0:
                    unique.append(seg_map[key])
                processed.add(key)
                processed.add(rev_key)
            else:
                # Normal boundary edge: keep 1 copy
                unique.append(seg_map[key])
                processed.add(key)

        return unique

    def build_chains(
        self, segments: List[Segment2D]
    ) -> Tuple[List[ReconstructedLoop], List[str]]:
        """
        Greedy path chaining with strict ambiguity checking.
        If an open endpoint has more than 1 candidate within snap_tol, it DOES NOT snap.
        """
        logs = []
        unused = list(segments)
        loops: List[ReconstructedLoop] = []

        while unused:
            cur_seg = unused.pop(0)
            chain: List[Point2D] = [cur_seg.p1, cur_seg.p2]
            traveled = cur_seg.length
            ambiguity_detected = False
            ambiguities = []

            extended = True
            while extended:
                extended = False
                start_pt = chain[0]
                end_pt = chain[-1]

                # Check if already geometrically closed:
                # Require traveled length > 3*snap_tol to avoid premature closure of micro-segments!
                min_travel = max(0.5, 3.0 * self.snap_tol)
                if len(chain) > 3 and traveled > min_travel and end_pt.dist_to(start_pt) <= self.snap_tol:
                    chain[-1] = start_pt
                    break

                # 1. Forward candidates from end_pt
                fwd_matches = []
                for idx, candidate in enumerate(unused):
                    d_s = end_pt.dist_to(candidate.p1)
                    d_e = end_pt.dist_to(candidate.p2)
                    if d_s <= self.snap_tol:
                        fwd_matches.append((idx, False, d_s))
                    elif d_e <= self.snap_tol:
                        fwd_matches.append((idx, True, d_e))

                if len(fwd_matches) == 1:
                    idx, rev, _ = fwd_matches[0]
                    cand = unused.pop(idx)
                    pts_to_add = [cand.p2] if not rev else [cand.p1]
                    traveled += cand.length
                    chain.extend(pts_to_add)
                    extended = True
                    continue
                elif len(fwd_matches) > 1:
                    msg = f"Ambiguity at end vertex {end_pt}: {len(fwd_matches)} candidates within {self.snap_tol} mm."
                    logs.append(msg)
                    ambiguities.append(msg)
                    ambiguity_detected = True
                    # Do not blindly branch! Stop forward extension.

                # 2. Backward candidates from start_pt
                bwd_matches = []
                for idx, candidate in enumerate(unused):
                    d_s = start_pt.dist_to(candidate.p1)
                    d_e = start_pt.dist_to(candidate.p2)
                    if d_e <= self.snap_tol:
                        bwd_matches.append((idx, False, d_e))
                    elif d_s <= self.snap_tol:
                        bwd_matches.append((idx, True, d_s))

                if len(bwd_matches) == 1:
                    idx, rev, _ = bwd_matches[0]
                    cand = unused.pop(idx)
                    pts_to_add = [cand.p1] if not rev else [cand.p2]
                    traveled += cand.length
                    chain = pts_to_add + chain
                    extended = True
                    continue
                elif len(bwd_matches) > 1:
                    msg = f"Ambiguity at start vertex {start_pt}: {len(bwd_matches)} candidates within {self.snap_tol} mm."
                    logs.append(msg)
                    ambiguities.append(msg)
                    ambiguity_detected = True
                    # Stop backward extension.

            # Determine closure
            min_travel = max(0.5, 3.0 * self.snap_tol)
            is_closed = len(chain) > 3 and traveled > min_travel and chain[0].dist_to(chain[-1]) <= self.snap_tol
            if is_closed:
                chain[-1] = chain[0]

            # Check if any endpoint touched the crop box
            is_inc = False
            if not is_closed:
                if self.is_near_crop(chain[0]) or self.is_near_crop(chain[-1]):
                    is_inc = True

            area = polygon_shoelace_area(chain) if is_closed else 0.0

            loops.append(
                ReconstructedLoop(
                    points=chain,
                    is_closed=is_closed,
                    is_outer=False,  # determined in hierarchy step
                    area=abs(area),
                    is_incomplete=is_inc,
                    ambiguities=ambiguities,
                )
            )

        return loops, logs

    def classify_hierarchy(
        self, loops: List[ReconstructedLoop]
    ) -> Tuple[Optional[ReconstructedLoop], List[ReconstructedLoop], List[ReconstructedLoop]]:
        """
        Classify loops into Outer Boundary, Cavity Holes, and Open Fragments.
        Outer boundary is the enclosing loop with maximum area.
        Holes are closed loops strictly contained inside the outer boundary.
        """
        closed_loops = [l for l in loops if l.is_closed]
        open_loops = [l for l in loops if not l.is_closed]

        if not closed_loops:
            return None, [], open_loops

        # Sort closed loops by area descending
        closed_loops.sort(key=lambda l: l.area, reverse=True)
        outer = closed_loops[0]
        outer.is_outer = True

        cavities: List[ReconstructedLoop] = []
        for l in closed_loops[1:]:
            # Check if l's first point is inside outer
            if point_in_polygon(l.points[0], outer.points):
                l.is_outer = False
                cavities.append(l)
            else:
                # Disconnected closed loop outside outer shell
                open_loops.append(l)

        return outer, cavities, open_loops

    def reconstruct(
        self, segments: List[Segment2D], part_id: str = "FERO_PART"
    ) -> ReconstructedSection:
        """Execute full topological reconstruction pipeline for a single component."""
        logs = []
        unique_segs = self.deduplicate_segments(segments)
        logs.append(f"Input segments: {len(segments)}, unique deduplicated: {len(unique_segs)}")

        loops, chain_logs = self.build_chains(unique_segs)
        logs.extend(chain_logs)

        outer, cavities, opens = self.classify_hierarchy(loops)

        # Net area calculation
        net_area = 0.0
        if outer:
            net_area = outer.area - sum(c.area for c in cavities)
            # Normalize outer winding to CCW (positive) and cavities to CW (negative)
            if polygon_shoelace_area(outer.points) < 0:
                outer.points.reverse()
            for c in cavities:
                if polygon_shoelace_area(c.points) > 0:
                    c.points.reverse()

        status = "ok"
        if any(l.ambiguities for l in loops):
            status = "ambiguous"
        elif any(o.is_incomplete for o in opens) or (outer and outer.is_incomplete):
            status = "incomplete"
        elif not outer:
            status = "failed"

        return ReconstructedSection(
            part_id=part_id,
            outer_boundary=outer,
            cavities=cavities,
            open_fragments=opens,
            net_material_area=round(net_area, 4),
            status=status,
            log_messages=logs,
        )


def export_section_to_dxf(
    section: ReconstructedSection,
    output_path: str,
    create_hatch: bool = True,
) -> Dict[str, Any]:
    """
    Save reconstructed section to AutoCAD R2013 DXF with BLOCK and INSERT.
    """
    doc = ezdxf.new("R2013", setup=True)
    doc.header["$INSUNITS"] = 4  # 4 = Millimeters
    msp = doc.modelspace()

    # Define dedicated engineering layers
    layers = [
        ("01_АЛЮМИНИЙ_КОНТУР", 7, 35),     # Main outer contour (white, 0.35mm)
        ("01_АЛЮМИНИЙ_ПОЛОСТЬ", 4, 25),    # Internal cavities/holes (cyan, 0.25mm)
        ("01_АЛЮМИНИЙ_МАТЕРИАЛ", 8, 13),   # Cross-section solid hatch (dark gray)
        ("00_ОБРЫВКИ_НЕЗАМКНУТЫЕ", 1, 18), # Incomplete/open fragments (red)
    ]
    for name, col, lw in layers:
        layer = doc.layers.add(name, color=col)
        layer.dxf.lineweight = lw

    block_name = f"BLOCK_{section.part_id.replace('.', '_')}"
    blk = doc.blocks.new(name=block_name)

    # 1. Outer boundary in block
    if section.outer_boundary:
        pts = [p.to_tuple() for p in section.outer_boundary.points]
        blk.add_lwpolyline(
            pts,
            close=True,
            dxfattribs={"layer": "01_АЛЮМИНИЙ_КОНТУР"}
        )

    # 2. Cavities in block
    for cav in section.cavities:
        pts = [p.to_tuple() for p in cav.points]
        blk.add_lwpolyline(
            pts,
            close=True,
            dxfattribs={"layer": "01_АЛЮМИНИЙ_ПОЛОСТЬ"}
        )

    # 3. Hatch
    if create_hatch and section.outer_boundary:
        try:
            hatch = blk.add_hatch(color=8, dxfattribs={"layer": "01_АЛЮМИНИЙ_МАТЕРИАЛ"})
            # Outer path
            outer_pts = [p.to_tuple() for p in section.outer_boundary.points]
            hatch.paths.add_polyline_path(outer_pts, is_closed=True, flags=1)  # 1 = external
            # Hole paths
            for cav in section.cavities:
                h_pts = [p.to_tuple() for p in cav.points]
                hatch.paths.add_polyline_path(h_pts, is_closed=True, flags=16)  # 16 = outermost/hole
        except Exception:
            pass

    # 4. Insert Block into ModelSpace at origin (0, 0)
    msp.add_blockref(block_name, (0.0, 0.0))

    # 5. Open fragments placed in ModelSpace for debugging
    for frag in section.open_fragments:
        pts = [p.to_tuple() for p in frag.points]
        if len(pts) >= 2:
            msp.add_lwpolyline(
                pts,
                close=frag.is_closed,
                dxfattribs={"layer": "00_ОБРЫВКИ_НЕЗАМКНУТЫЕ"}
            )

    doc.saveas(output_path)

    return {
        "success": True,
        "output_path": output_path,
        "block_name": block_name,
        "outer_loops": 1 if section.outer_boundary else 0,
        "cavity_loops": len(section.cavities),
        "open_fragments": len(section.open_fragments),
        "net_material_area": section.net_material_area,
        "status": section.status,
    }
