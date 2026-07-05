"""
Standard clothing size charts, used as an easy calibration anchor.

Picking a known size fills in an approximate body circumference (the size
range's midpoint), which the pipeline uses as its one-time per-user
calibration value. Less exact than a tape measurement (vanity sizing varies
~1-2 in between brands) but far easier for the end user.
"""

CM_PER_IN = 2.54

# Women's jeans size -> hip circumference range (inches).
WOMENS_JEANS_HIP_IN = {
    "24": (33.75, 34.75),
    "25": (34.75, 35.75),
    "26": (35.75, 36.75),
    "27": (36.75, 37.75),
    "28": (37.75, 38.75),
    "29": (38.75, 39.75),
    "30": (39.75, 40.75),
    "31": (40.75, 41.75),
    "32": (41.75, 42.75),
}

# Chart name -> (body part it calibrates, {size: (low_in, high_in)}).
# Add more charts (e.g. men's) here with the same shape.
SIZE_CHARTS = {
    "Women's jeans (hip)": ("hip", WOMENS_JEANS_HIP_IN),
}


def calibration_from_size(chart_name, size):
    """Return (part, cm) for the midpoint of a size, or (None, None)."""
    if chart_name not in SIZE_CHARTS:
        return None, None

    part, chart = SIZE_CHARTS[chart_name]
    if size not in chart:
        return None, None

    low, high = chart[size]
    return part, round((low + high) / 2 * CM_PER_IN, 1)
