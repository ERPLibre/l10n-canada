# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pure helpers of the payroll remunerated hours."""


def covered_days(intervals):
    """Return the number of days covered by the union of ``intervals``.

    ``intervals`` is an iterable of ``(start, end)`` dates, both inclusive.
    Overlapping or repeated intervals count their common days once, so two
    payslips of the same week cover seven days, not fourteen.
    """
    total = 0
    current_start = current_end = None
    for start, end in sorted(intervals):
        if current_end is None or (start - current_end).days > 1:
            if current_end is not None:
                total += (current_end - current_start).days + 1
            current_start, current_end = start, end
        elif end > current_end:
            current_end = end
    if current_end is not None:
        total += (current_end - current_start).days + 1
    return total
