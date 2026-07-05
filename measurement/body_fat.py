import numpy as np


def navy_body_fat(measurements, height_cm, gender):
    """
    US Navy body-fat estimate (metric form, all inputs in cm). Needs no weight.
    Men use waist + neck; women additionally use hip.
    """
    waist = measurements.get("waist", 0)
    neck = measurements.get("neck", 0)
    hip = measurements.get("hip", 0)

    if waist <= 0 or neck <= 0 or height_cm <= 0:
        return 0

    if gender == "female":
        value = waist + hip - neck
        if value <= 0:
            return 0
        bf = 495 / (1.29579 - 0.35004 * np.log10(value)
                    + 0.22100 * np.log10(height_cm)) - 450
    else:
        value = waist - neck
        if value <= 0:
            return 0
        bf = 495 / (1.0324 - 0.19077 * np.log10(value)
                    + 0.15456 * np.log10(height_cm)) - 450

    return round(float(bf), 2)


def bmi(weight_kg, height_cm):
    if not weight_kg or height_cm <= 0:
        return 0
    h = height_cm / 100.0
    return round(float(weight_kg / (h * h)), 2)


def deurenberg_body_fat(bmi_value, age, gender):
    """Weight-based body-fat cross-check (needs BMI + age)."""
    if not bmi_value or not age:
        return 0
    sex = 1 if gender == "male" else 0
    bf = 1.20 * bmi_value + 0.23 * age - 10.8 * sex - 5.4
    return round(float(bf), 2)


def estimate_weight_from_volume(vertices, faces, area_correction=1.0,
                                density_kg_m3=1010.0):
    """
    Estimate body weight from the watertight mesh volume (vertices in metres).
    area_correction rescales the cross-section for the per-user calibration
    (mesh height is correct but width/depth carry the silhouette bias).
    """
    import trimesh

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    volume = abs(mesh.volume) * area_correction

    return round(float(volume * density_kg_m3), 2)
