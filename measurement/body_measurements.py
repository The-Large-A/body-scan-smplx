import os
import json
import numpy as np
import config
from scipy.spatial import ConvexHull
from config import HEIGHT_RATIOS, SMPL_MODEL_PATH
from measurement.body_fat import (
    navy_body_fat, bmi, deurenberg_body_fat, estimate_weight_from_volume)

# Torso parts measured directly from the rotation silhouettes.
TORSO_PARTS = ["chest", "waist", "hip"]

# Limb parts measured from the SMPL-X mesh via vertex segmentation.
# (output name, SMPL-X segmentation part, "max"=thickest / "min"=thinnest slice)
LIMB_PARTS = [
    ("bicep",   "Arm",     "max"),
    ("forearm", "ForeArm", "max"),
    ("wrist",   "ForeArm", "min"),
    ("thigh",   "UpLeg",   "max"),
    ("calf",    "Leg",     "max"),
]

# Every circumference output shares the systematic silhouette bias, so the
# per-user calibration factor applies to all of them.
CALIBRATED_PARTS = TORSO_PARTS + [name for name, _, _ in LIMB_PARTS] + ["neck"]


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
# LIMB MEASUREMENTS (SMPL-X vertex segmentation)
# --------------------------------------------------
_SEGMENTATION = None


def _segmentation():
    global _SEGMENTATION
    if _SEGMENTATION is None:
        path = os.path.join(SMPL_MODEL_PATH, "smplx_vert_segmentation.json")
        with open(path) as f:
            _SEGMENTATION = json.load(f)
    return _SEGMENTATION


def limb_circumferences(vertices, part):
    """
    Circumference (cm) sampled along one limb. The limb's own long axis is
    found by PCA, then the mesh is sliced perpendicular to it and each slice's
    perimeter is measured in the perpendicular plane.
    """
    pts = vertices[_segmentation()[part]]
    center = pts.mean(axis=0)

    _, _, vt = np.linalg.svd(pts - center)
    axis, e1, e2 = vt[0], vt[1], vt[2]

    proj = (pts - center) @ axis
    lo, hi = proj.min(), proj.max()
    length = hi - lo

    circs = []
    for t in np.linspace(lo + 0.1 * length, hi - 0.1 * length, 25):
        band = np.abs(proj - t) < 0.06 * length
        pb = pts[band]
        if len(pb) < 10:
            continue
        pts2d = np.column_stack([(pb - center) @ e1, (pb - center) @ e2])
        circs.append(compute_perimeter(pts2d) * 100)

    return np.array(circs)


def limb_measurement(vertices, seg_part, mode):
    """Average the left/right thickest ("max") or thinnest ("min") slice."""
    values = []
    for side in ("left", "right"):
        circs = limb_circumferences(vertices, side + seg_part)
        circs = circs[circs > 0]
        if len(circs):
            values.append(circs.max() if mode == "max" else circs.min())

    return sum(values) / len(values) if values else 0


# --------------------------------------------------
# TORSO FROM SILHOUETTES (front width + side depth across the spin)
# --------------------------------------------------
def ellipse_perimeter(a, b):
    return np.pi * (3*(a+b) - np.sqrt((3*a+b)*(a+3*b)))


def silhouette_extents(masks, ratio, height_cm):
    """
    Horizontal body extent (cm) at a body-height fraction, one value per frame.
    Each frame self-scales by its own pixel height so a full rotation yields
    the frontal width (max) at one extreme and the side depth (min) at the other.
    """
    extents = []

    for mask in masks:

        ys, xs = np.where(mask)

        if len(ys) == 0:
            continue

        y_top, y_bot = ys.min(), ys.max()
        pixel_height = y_bot - y_top

        if pixel_height < 200:
            continue

        row = y_bot - ratio * pixel_height
        band = np.abs(ys - row) <= max(1, int(0.01 * pixel_height))

        if band.any():
            extents.append((xs[band].max() - xs[band].min()) * height_cm / pixel_height)

    return np.array(extents)


def torso_circumference(masks, ratio, height_cm):

    extents = silhouette_extents(masks, ratio, height_cm)

    if len(extents) < 5:
        return 0

    width = np.percentile(extents, 90)   # frontal
    depth = np.percentile(extents, 10)   # lateral

    return ellipse_perimeter(width / 2, depth / 2)


# --------------------------------------------------
# MAIN FUNCTION
# --------------------------------------------------
def compute_measurements(vertices, masks, faces):

    height_cm = config.USER_HEIGHT_CM
    gender = config.GENDER

    results = {}

    # torso: measured directly from the rotation silhouettes
    for part in TORSO_PARTS:
        results[part] = torso_circumference(masks, HEIGHT_RATIOS[part], height_cm)

    # limbs (arms + legs): from the mesh via vertex segmentation
    for name, seg_part, mode in LIMB_PARTS:
        results[name] = limb_measurement(vertices, seg_part, mode)

    # neck (single, non-lateral segment; median slice = typical neck girth)
    neck = limb_circumferences(vertices, "neck")
    neck = neck[neck > 0]
    results["neck"] = float(np.median(neck)) if len(neck) else 0

    # optional one-time per-user calibration (removes systematic silhouette bias)
    k = 1.0
    if config.CALIBRATION_PART and config.CALIBRATION_CM and results.get(config.CALIBRATION_PART):
        k = config.CALIBRATION_CM / results[config.CALIBRATION_PART]
        for part in CALIBRATED_PARTS:
            results[part] *= k

    # body composition
    weight = config.USER_WEIGHT_KG
    if not weight:
        weight = estimate_weight_from_volume(vertices, faces, area_correction=k * k)

    results["weight_kg"] = weight
    results["bmi"] = bmi(weight, height_cm)
    results["body_fat_%"] = navy_body_fat(results, height_cm, gender)

    if config.USER_AGE and weight:
        results["body_fat_bmi_%"] = deurenberg_body_fat(results["bmi"], config.USER_AGE, gender)

    return results