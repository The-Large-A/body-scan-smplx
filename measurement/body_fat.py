import numpy as np


def estimate_body_fat(measurements, height_cm, gender="male"):

    waist = measurements.get("waist", 0)
    neck = measurements.get("neck", 35)   # fallback
    hip = measurements.get("hip", 0)

    if waist == 0 or height_cm == 0:
        return 0

    height = height_cm

    if gender == "male":

        body_fat = 86.010 * np.log10(waist - neck) \
                   - 70.041 * np.log10(height) \
                   + 36.76

    else:
        body_fat = 163.205 * np.log10(waist + hip - neck) \
                   - 97.684 * np.log10(height) \
                   - 78.387

    return round(float(body_fat), 2)