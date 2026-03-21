"""Unit tests for Hebrew TeX helpers (no Manim scene render)."""

import unittest

import numpy as np

from hebrew_utils import _partition_hebrew_for_collapsed


class _FakeLeaf:
    __slots__ = ("_x", "tag")

    def __init__(self, x: float, tag: str = ""):
        self._x = x
        self.tag = tag

    def get_center(self):
        return np.array([self._x, 0.0, 0.0])


class TestPartitionHebrewCollapsed(unittest.TestCase):
    def test_three_hebrew_two_math_mixed_line(self):
        """
        H,H,M,H,M — e.g. משפט, תהא, f(x), phrase, [a,b].
        Spatial (RTL): right cluster (משפט, תהא), middle (phrase), left math [a,b].
        """
        strings = [
            "משפט:",
            "תהא",
            r"$f(x)$",
            "פונקציה רציפה בקטע",
            r"$[a,b]$",
        ]
        ms = _FakeLeaf(10.0, "משפט")
        th = _FakeLeaf(8.0, "תהא")
        mid = _FakeLeaf(2.0, "mid")
        hebrew_leaves = [ms, th, mid]

        math_glyphs_by_idx = {
            2: [_FakeLeaf(5.0), _FakeLeaf(6.0)],  # f(x) — right math band
            4: [_FakeLeaf(-1.0), _FakeLeaf(0.0)],  # [a,b] — left math band
        }

        out = _partition_hebrew_for_collapsed(strings, hebrew_leaves, math_glyphs_by_idx)

        self.assertEqual([m.tag for m in out[0]], ["משפט"])
        self.assertEqual([m.tag for m in out[1]], ["תהא"])
        self.assertEqual([m.tag for m in out[3]], ["mid"])
        self.assertNotIn(2, out)
        self.assertNotIn(4, out)

    def test_split_hebrew_cluster_two_words_largest_gap(self):
        strings = ["a", "b", r"$x$", "c", r"$y$"]
        # Three Hebrew leaves: two on the right (large gap between word1 and word2), one between math
        leaves = [
            _FakeLeaf(20.0, "w0a"),
            _FakeLeaf(19.0, "w0b"),
            _FakeLeaf(5.0, "w0c"),
            _FakeLeaf(4.0, "w1a"),
            _FakeLeaf(3.9, "w1b"),
            _FakeLeaf(1.5, "between"),
        ]
        math_glyphs_by_idx = {
            2: [_FakeLeaf(2.2), _FakeLeaf(2.8)],
            4: [_FakeLeaf(-0.5), _FakeLeaf(0.5)],
        }
        out = _partition_hebrew_for_collapsed(strings, leaves, math_glyphs_by_idx)
        # Index 3 = between math
        self.assertTrue(any(m.tag == "between" for m in out[3]))
        # Right cluster: w0* and w1* — largest gap should separate w0 block from w1 block
        tags0 = {m.tag for m in out[0]}
        tags1 = {m.tag for m in out[1]}
        self.assertTrue(tags0 & {"w0a", "w0b", "w0c"} or tags0)
        self.assertTrue(tags1 & {"w1a", "w1b"} or tags1)
        self.assertEqual(tags0 & tags1, set())

    def test_two_hebrew_two_math_h_m_h_m(self):
        """H, M, H, M — middle Hebrew in gap; first Hebrew = outer (right + left of math bands)."""
        strings = ["a", r"$x$", "b", r"$y$"]
        h_right = _FakeLeaf(9.0, "lead")
        h_mid = _FakeLeaf(2.0, "mid")
        h_left = _FakeLeaf(-2.0, "left")
        hebrew_leaves = [h_right, h_mid, h_left]
        math_glyphs_by_idx = {
            1: [_FakeLeaf(5.0), _FakeLeaf(6.0)],
            3: [_FakeLeaf(-1.0), _FakeLeaf(0.0)],
        }
        out = _partition_hebrew_for_collapsed(strings, hebrew_leaves, math_glyphs_by_idx)
        self.assertEqual({m.tag for m in out[0]}, {"lead", "left"})
        self.assertEqual([m.tag for m in out[2]], ["mid"])

    def test_single_hebrew_one_math_all_hebrew_to_one_index(self):
        """One Hebrew segment + one math — every Hebrew leaf maps to index 0."""
        strings = ["לפני ", r"$\displaystyle\int_0^1$"]
        leaves = [_FakeLeaf(5.0, "h1"), _FakeLeaf(4.0, "h2")]
        math_glyphs_by_idx = {1: [_FakeLeaf(2.0), _FakeLeaf(3.0)]}
        out = _partition_hebrew_for_collapsed(strings, leaves, math_glyphs_by_idx)
        self.assertEqual({m.tag for m in out[0]}, {"h1", "h2"})

    def test_pure_hebrew_three_segments_no_math(self):
        """Three ``Tex`` text args, no math — split by largest gaps (RTL)."""
        strings = ["א", "ב", "ג"]
        leaves = [
            _FakeLeaf(20.0, "g1"),
            _FakeLeaf(19.0, "g1b"),
            _FakeLeaf(8.0, "g2"),
            _FakeLeaf(7.0, "g2b"),
            _FakeLeaf(0.5, "g3"),
        ]
        out = _partition_hebrew_for_collapsed(strings, leaves, {})
        self.assertEqual(len(out), 3)
        self.assertTrue(any(m.tag.startswith("g1") for m in out[0]))
        self.assertTrue(any(m.tag.startswith("g2") for m in out[1]))
        self.assertTrue(any(m.tag.startswith("g3") for m in out[2]))

    def test_two_hebrew_one_math_math_last(self):
        """H, H, M — two leading Hebrew indices before one math; split in leading zone."""
        strings = ["ו", "ג", r"$\bigcup$"]
        w0 = _FakeLeaf(10.0, "w0")
        w1 = _FakeLeaf(8.5, "w1")
        math_glyphs_by_idx = {2: [_FakeLeaf(1.0), _FakeLeaf(0.0)]}
        out = _partition_hebrew_for_collapsed(strings, [w0, w1], math_glyphs_by_idx)
        self.assertEqual([m.tag for m in out[0]], ["w0"])
        self.assertEqual([m.tag for m in out[1]], ["w1"])

    def test_h_m_h_leading_and_trailing(self):
        """H, M, H — Hebrew before first math (right) and after last math (left), RTL."""
        strings = ["לפני", r"$I$", "אחרי"]
        h_before = _FakeLeaf(5.0, "before")
        h_after = _FakeLeaf(-2.0, "after")
        math_glyphs_by_idx = {1: [_FakeLeaf(0.0), _FakeLeaf(1.0)]}
        out = _partition_hebrew_for_collapsed(strings, [h_before, h_after], math_glyphs_by_idx)
        self.assertEqual([m.tag for m in out[0]], ["before"])
        self.assertEqual([m.tag for m in out[2]], ["after"])

    def test_hebrew_leaf_inside_math_x_span_goes_to_leading_segment(self):
        """Collapsed SVG: a Hebrew path whose x lies inside the math band is tied to Hebrew before math."""
        strings = ["קדם", r"$Z$", "אחר"]
        stray = _FakeLeaf(0.5, "stray")
        h_before = _FakeLeaf(5.0, "before")
        h_after = _FakeLeaf(-2.0, "after")
        math_glyphs_by_idx = {1: [_FakeLeaf(0.0), _FakeLeaf(1.0)]}
        out = _partition_hebrew_for_collapsed(
            strings,
            [stray, h_before, h_after],
            math_glyphs_by_idx,
        )
        self.assertEqual({m.tag for m in out[0]}, {"stray", "before"})
        self.assertEqual([m.tag for m in out[2]], ["after"])


if __name__ == "__main__":
    unittest.main()
