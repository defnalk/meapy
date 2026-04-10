"""Unit tests for meapy._validation."""

from __future__ import annotations

import pytest

from meapy._validation import (
    require_in_range,
    require_non_negative,
    require_positive,
    require_same_length,
)


class TestRequirePositive:
    def test_passes_for_positive(self):
        require_positive("x", 1.0)
        require_positive("x", 0.001)

    @pytest.mark.parametrize("val", [0.0, -1.0, -0.001])
    def test_raises_for_nonpositive(self, val):
        with pytest.raises(ValueError, match="positive"):
            require_positive("x", val)


class TestRequireNonNegative:
    def test_passes_for_zero(self):
        require_non_negative("x", 0.0)

    def test_passes_for_positive(self):
        require_non_negative("x", 1.0)

    def test_raises_for_negative(self):
        with pytest.raises(ValueError, match="non-negative"):
            require_non_negative("x", -0.001)


class TestRequireInRange:
    def test_inclusive_lo_exclusive_hi(self):
        require_in_range("x", 0.0, 0.0, 1.0)
        with pytest.raises(ValueError):
            require_in_range("x", 1.0, 0.0, 1.0)

    def test_exclusive_lo(self):
        with pytest.raises(ValueError):
            require_in_range("x", 0.0, 0.0, 1.0, lo_inclusive=False)

    def test_inclusive_hi(self):
        require_in_range("x", 1.0, 0.0, 1.0, hi_inclusive=True)


class TestRequireSameLength:
    def test_same_length_passes(self):
        require_same_length(a=[1, 2, 3], b=[4, 5, 6])

    def test_different_length_raises(self):
        with pytest.raises(ValueError, match="same length"):
            require_same_length(a=[1, 2], b=[4, 5, 6])

    def test_empty_call_passes(self):
        require_same_length()
