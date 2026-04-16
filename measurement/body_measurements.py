import numpy as np
from config import HEIGHT_RATIOS
from scipy.spatial import ConvexHull
from measurement.body_fat import estimate_body_fat
from config import USER_HEIGHT_CM


# --------------------------------------------------
# SMOOTHING (reduces mesh noise)
# --------------------------------------------------
def smooth_vertices(vertices, iterations=2):

    smoothed = vertices.copy()

    for _ in range(iterations):
        smoothed = (smoothed +
                    np.roll(smoothed, 1, axis=0) +
                    np.roll(smoothed, -1, axis=0)) / 3

    return smoothed


# --------------------------------------------------
# BODY AXIS (HEAD → PELVIS)
# --------------------------------------------------
def compute_body_axis(vertices):

    y = vertices[:,1]

    pelvis = np.mean(vertices[y < np.percentile(y, 20)], axis=0)
    head = np.mean(vertices[y > np.percentile(y, 95)], axis=0)

    axis = head - pelvis
    axis = axis / np.linalg.norm(axis)

    return axis


# --------------------------------------------------
# CONVEX HULL PERIMETER
# --------------------------------------------------
def compute_perimeter(points):

    if len(points) < 10:
        return 0

    hull = ConvexHull(points)

    perimeter = 0

    for i in range(len(hull.vertices)):
        p1 = points[hull.vertices[i]]
        p2 = points[hull.vertices[(i+1) % len(hull.vertices)]]
        perimeter += np.linalg.norm(p1 - p2)

    return perimeter


# --------------------------------------------------
# BODY MEASUREMENTS (TORSO + LEGS)
# --------------------------------------------------
def circumference_at_ratio(vertices, ratio):

    axis = compute_body_axis(vertices)

    proj = vertices @ axis

    min_h = proj.min()
    max_h = proj.max()

    height = min_h + ratio * (max_h - min_h)

    thickness = 0.02 * (max_h - min_h)

    slice_mask = np.abs(proj - height) < thickness

    pts = vertices[slice_mask]

    if len(pts) < 20:
        return 0

    pts2d = pts[:, [0,2]]

    center = np.mean(pts2d, axis=0)
    pts2d -= center

    perimeter = compute_perimeter(pts2d)

    return perimeter * 100


# --------------------------------------------------
# ARM MEASUREMENTS (LEFT + RIGHT SUPPORT)
# --------------------------------------------------
def arm_circumference(vertices, ratio, side="right"):

    x = vertices[:,0]

    if side == "right":
        arm_vertices = vertices[x > np.percentile(x, 90)]
    else:
        arm_vertices = vertices[x < np.percentile(x, 10)]

    if len(arm_vertices) < 30:
        return 0

    arm_x = arm_vertices[:,0]

    min_x = arm_x.min()
    max_x = arm_x.max()

    slice_x = min_x + ratio * (max_x - min_x)

    thickness = 0.01 * (max_x - min_x)

    slice_mask = np.abs(x - slice_x) < thickness

    pts = vertices[slice_mask]

    # isolate correct side
    if side == "right":
        pts = pts[pts[:,0] > np.percentile(x, 90)]
    else:
        pts = pts[pts[:,0] < np.percentile(x, 10)]

    if len(pts) < 10:
        return 0

    pts2d = pts[:, [1,2]]

    center = np.mean(pts2d, axis=0)
    pts2d -= center

    perimeter = compute_perimeter(pts2d)

    return perimeter * 100


# --------------------------------------------------
# MAIN FUNCTION
# --------------------------------------------------
def compute_measurements(vertices):

    # 🔥 smoothing applied here
    vertices = smooth_vertices(vertices)

    results = {}

    # torso + legs
    for part, ratio in HEIGHT_RATIOS.items():
        results[part] = circumference_at_ratio(vertices, ratio)

    # arms (left + right averaging)
    right_upper = arm_circumference(vertices, 0.35, "right")
    left_upper  = arm_circumference(vertices, 0.35, "left")

    right_wrist = arm_circumference(vertices, 0.80, "right")
    left_wrist  = arm_circumference(vertices, 0.80, "left")

    results["upper_arm"] = (right_upper + left_upper) / 2
    results["wrist"] = (right_wrist + left_wrist) / 2
    results["body_fat_%"] = estimate_body_fat(
        results,
        USER_HEIGHT_CM,
        gender="male"  # change if needed
    )

    return results