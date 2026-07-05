import numpy as np


def select_views(joints_list):
    """
    Pick the frame indices with the widest and narrowest shoulder spread.
    Widest shoulders => front-facing view; narrowest => side view.
    Shoulder landmarks are MediaPipe indices 11 (left) and 12 (right).
    """
    widths = [abs(j[11][0] - j[12][0]) for j in joints_list]

    front_idx = int(np.argmax(widths))
    side_idx = int(np.argmin(widths))

    return front_idx, side_idx
