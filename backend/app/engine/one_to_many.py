"""Exact subset-sum on paise for payments that cover several invoices, or invoices paid in parts."""
from __future__ import annotations

from itertools import combinations

TOLERANCE_PAISE = 100
MAX_CANDIDATES = 15


def find_subset(amounts: list[int], target: int, max_size: int = 4, tolerance: int = TOLERANCE_PAISE) -> tuple[int, ...] | None:
    """Positions of the fewest amounts that add up to the target within the tolerance; earlier positions win ties."""
    amounts = amounts[:MAX_CANDIDATES]
    for size in range(1, min(max_size, len(amounts)) + 1):
        for combo in combinations(range(len(amounts)), size):
            if abs(sum(amounts[i] for i in combo) - target) <= tolerance:
                return combo
    return None
