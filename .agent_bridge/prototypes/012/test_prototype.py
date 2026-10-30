"""
Synthetic Test Suite for Prototype 012 (Topological Section Reconstructor)
==========================================================================
Verifies required edge cases:
1. Part with an interior hole/cavity (distinguishing outer vs inner loops).
2. Part with an open groove/notch (avoiding false bridges over open channels).
3. Two adjacent/touching parts (avoiding false merger of separate profiles).
4. Small functional tooth / lip (preservation of sub-millimeter features).
5. Overlapping / segmented fill slices (union without void artifacts).
6. Ambiguous gap with multiple equidistant candidates (logging ambiguity, no blind snap).
7. Part intersected by crop boundary (marking incomplete, no false crop edge sealing).
"""

import sys
import unittest
from section_reconstructor import (
    Point2D,
    Segment2D,
    TopologicalSectionReconstructor,
    export_section_to_dxf,
)


class TestSectionReconstructor(unittest.TestCase):

    def test_01_part_with_cavity_hole(self):
        """Outer 100x100 square with an internal 40x40 cavity hole."""
        # Outer square: (0,0) -> (100,0) -> (100,100) -> (0,100) -> (0,0)
        outer_pts = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        outer_segs = [
            Segment2D(outer_pts[0], outer_pts[1]),
            Segment2D(outer_pts[1], outer_pts[2]),
            Segment2D(outer_pts[2], outer_pts[3]),
            Segment2D(outer_pts[3], outer_pts[0]),
        ]
        # Hole: (30,30) -> (70,30) -> (70,70) -> (30,70) -> (30,30)
        hole_pts = [Point2D(30, 30), Point2D(70, 30), Point2D(70, 70), Point2D(30, 70)]
        hole_segs = [
            Segment2D(hole_pts[0], hole_pts[1]),
            Segment2D(hole_pts[1], hole_pts[2]),
            Segment2D(hole_pts[2], hole_pts[3]),
            Segment2D(hole_pts[3], hole_pts[0]),
        ]

        recon = TopologicalSectionReconstructor(snap_tolerance=0.05)
        res = recon.reconstruct(outer_segs + hole_segs, part_id="TEST_CAVITY")

        self.assertEqual(res.status, "ok")
        self.assertIsNotNone(res.outer_boundary)
        self.assertEqual(len(res.cavities), 1)
        # Outer area: 10,000, Hole area: 1,600 -> Net: 8,400
        self.assertAlmostEqual(res.outer_boundary.area, 10000.0, places=2)
        self.assertAlmostEqual(res.cavities[0].area, 1600.0, places=2)
        self.assertAlmostEqual(res.net_material_area, 8400.0, places=2)

    def test_02_open_groove_not_bridged(self):
        """U-channel (open groove) must stay open and part of the outer perimeter, not converted to hole."""
        # U-shape profile: outer 50x50 with a 20x30 open groove at top
        pts = [
            Point2D(0, 0), Point2D(50, 0), Point2D(50, 50),
            Point2D(35, 50), Point2D(35, 20), Point2D(15, 20), Point2D(15, 50),
            Point2D(0, 50)
        ]
        segs = [Segment2D(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]

        recon = TopologicalSectionReconstructor(snap_tolerance=0.05)
        res = recon.reconstruct(segs, part_id="TEST_GROOVE")

        self.assertEqual(res.status, "ok")
        self.assertIsNotNone(res.outer_boundary)
        self.assertEqual(len(res.cavities), 0, "Open groove must not be classified as an internal hole!")
        self.assertEqual(len(res.outer_boundary.points), 9)  # 8 vertices + closed repeat
        # Expected area: 50*50 - 20*30 = 2500 - 600 = 1900
        self.assertAlmostEqual(res.net_material_area, 1900.0, places=2)

    def test_03_two_adjacent_touching_parts_not_merged(self):
        """Two separate profiles touching along a contact face (gap = 0.02 mm <= snap_tol).
           When clustered or reconstructed individually, they must not cross-contaminate."""
        # Part A: X [0..20], Y [0..20]
        ptsA = [Point2D(0, 0), Point2D(20, 0), Point2D(20, 20), Point2D(0, 20)]
        segsA = [Segment2D(ptsA[i], ptsA[(i + 1) % 4]) for i in range(4)]

        # Part B: X [20.02..40], Y [0..20] (touching contact with 0.02mm clearance)
        ptsB = [Point2D(20.02, 0), Point2D(40, 0), Point2D(40, 20), Point2D(20.02, 20)]
        segsB = [Segment2D(ptsB[i], ptsB[(i + 1) % 4]) for i in range(4)]

        recon = TopologicalSectionReconstructor(snap_tolerance=0.01)  # Strict clearance tolerance
        resA = recon.reconstruct(segsA, part_id="PART_A")
        resB = recon.reconstruct(segsB, part_id="PART_B")

        self.assertEqual(resA.status, "ok")
        self.assertEqual(resB.status, "ok")
        self.assertAlmostEqual(resA.net_material_area, 400.0, places=2)
        self.assertAlmostEqual(resB.net_material_area, 399.6, places=1)

    def test_04_small_functional_tooth_preserved(self):
        """Small crimp tooth of width 0.40 mm and height 1.5 mm must NOT be filtered out or simplified away."""
        pts = [
            Point2D(0, 0), Point2D(30, 0), Point2D(30, 10),
            Point2D(15.4, 10), Point2D(15.4, 11.5), Point2D(15.0, 11.5), Point2D(15.0, 10),
            Point2D(0, 10)
        ]
        segs = [Segment2D(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]

        recon = TopologicalSectionReconstructor(snap_tolerance=0.05)
        res = recon.reconstruct(segs, part_id="TEST_TOOTH")

        self.assertEqual(res.status, "ok")
        self.assertIsNotNone(res.outer_boundary)
        # Check that the tooth apex is preserved
        apex_present = any(abs(p.x - 15.2) < 0.3 and abs(p.y - 11.5) < 0.01 for p in res.outer_boundary.points)
        self.assertTrue(apex_present, "Small 0.4mm tooth apex was lost in reconstruction!")
        # Base area 300 + tooth area (0.4 * 1.5 = 0.6) = 300.6 mm2
        self.assertAlmostEqual(res.net_material_area, 300.6, places=2)

    def test_05_overlapping_fill_slices(self):
        """Two overlapping or abutting slices (representing scanline decomposition of material)."""
        # Slice 1: X [0..10], Y [0..5]
        s1 = [
            Segment2D(Point2D(0, 0), Point2D(10, 0)),
            Segment2D(Point2D(10, 0), Point2D(10, 5)),
            Segment2D(Point2D(10, 5), Point2D(0, 5)),
            Segment2D(Point2D(0, 5), Point2D(0, 0)),
        ]
        # Slice 2: X [0..10], Y [5..10] sharing the interface edge (10,5) -> (0,5)
        s2 = [
            Segment2D(Point2D(0, 5), Point2D(10, 5)),
            Segment2D(Point2D(10, 5), Point2D(10, 10)),
            Segment2D(Point2D(10, 10), Point2D(0, 10)),
            Segment2D(Point2D(0, 10), Point2D(0, 5)),
        ]
        # Combined segments (with interface duplicate)
        recon = TopologicalSectionReconstructor(snap_tolerance=0.05)
        # Deduplication removes duplicate interface
        res = recon.reconstruct(s1 + s2, part_id="TEST_SLICES")

        self.assertEqual(res.status, "ok")
        self.assertIsNotNone(res.outer_boundary)
        # Combined 10x10 square = 100 mm2
        self.assertAlmostEqual(res.net_material_area, 100.0, places=2)

    def test_06_ambiguous_branch_gap_logged(self):
        """An open endpoint equidistant to two candidates must trigger an ambiguity log, not blind snap."""
        # Main chain from (0,0) to (10,0)
        main_seg = Segment2D(Point2D(0, 0), Point2D(10, 0))
        # Two conflicting candidates at distance 0.03 mm from (10,0)
        cand1 = Segment2D(Point2D(10.03, 0.01), Point2D(20, 0))
        cand2 = Segment2D(Point2D(10.03, -0.01), Point2D(20, 0))

        recon = TopologicalSectionReconstructor(snap_tolerance=0.05)
        res = recon.reconstruct([main_seg, cand1, cand2], part_id="TEST_AMBIGUOUS")

        self.assertIn("ambiguous", res.status)
        self.assertTrue(len(res.log_messages) > 0)
        has_ambiguity_log = any("Ambiguity" in msg for msg in res.log_messages)
        self.assertTrue(has_ambiguity_log, "Ambiguity at branching vertex was not detected!")

    def test_07_crop_intersected_part_marked_incomplete(self):
        """A profile wall crossing the crop boundary must be flagged incomplete, not sealed along crop."""
        crop_box = (0.0, 0.0, 50.0, 50.0)
        # Open polyline touching the crop box edge at X=50
        segs = [
            Segment2D(Point2D(10, 10), Point2D(30, 10)),
            Segment2D(Point2D(30, 10), Point2D(50, 10)),  # touches crop boundary
        ]

        recon = TopologicalSectionReconstructor(
            snap_tolerance=0.05,
            crop_box=crop_box,
            crop_margin=0.2,
        )
        res = recon.reconstruct(segs, part_id="TEST_CROP")

        self.assertEqual(res.status, "incomplete")
        self.assertTrue(len(res.open_fragments) > 0)
        self.assertTrue(res.open_fragments[0].is_incomplete)


if __name__ == "__main__":
    unittest.main()
