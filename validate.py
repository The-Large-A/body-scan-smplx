"""
Validation harness for the Body Scan pipeline.

Runs the pipeline on a video with KNOWN tape measurements and prints
predicted-vs-truth with per-item error and overall MAE. This is the
objective check used to judge whether a change improves accuracy.

Subject stats and measurements live in validation_data.py (gitignored).
Copy validation_data.example.py to validation_data.py and fill it in.

Usage:
    python validate.py
"""

import config

try:
    from validation_data import SUBJECT
except ImportError:
    raise SystemExit(
        "Missing validation_data.py. Copy validation_data.example.py to "
        "validation_data.py and fill in a subject's real measurements.")

# Apply the subject's known values before running (the pipeline reads config).
config.USER_HEIGHT_CM = SUBJECT["height_cm"]
config.GENDER = SUBJECT["gender"]
config.USER_WEIGHT_KG = SUBJECT["weight_kg"]
config.USER_AGE = SUBJECT["age"]

from pipeline import run_pipeline

VIDEO = SUBJECT["video"]
GROUND_TRUTH = SUBJECT["ground_truth"]

# Map a ground-truth name to the key the pipeline outputs.
PRED_KEY = {
    "chest": "chest",
    "waist": "waist",
    "thigh": "thigh",
    "calf": "calf",
    "bicep": "bicep",
    "forearm": "forearm",
    "wrist": "wrist",
}


def report(measurements):
    print("\n" + "=" * 52)
    print(f"{'measurement':<12}{'truth':>8}{'pred':>10}{'error':>10}")
    print("-" * 52)

    errors = []
    for name, truth in GROUND_TRUTH.items():
        pred_key = PRED_KEY.get(name)
        pred = measurements.get(pred_key) if pred_key else None

        if pred is None:
            print(f"{name:<12}{truth:>8}{'n/a':>10}{'n/a':>10}")
            continue

        err = abs(pred - truth)
        errors.append(err)
        print(f"{name:<12}{truth:>8}{pred:>10.1f}{err:>10.1f}")

    print("-" * 52)
    if errors:
        mae = sum(errors) / len(errors)
        print(f"{'MAE (cm)':<12}{'':>8}{'':>10}{mae:>10.2f}")
    print("=" * 52)

    extra = {k: v for k, v in measurements.items()
             if k not in PRED_KEY.values()}
    if extra:
        print("\nOther outputs:")
        for k, v in extra.items():
            print(f"  {k}: {round(v, 2)}")

    # Per-user calibration demo: anchor on waist, check every other part.
    waist_pred = measurements.get("waist")
    if waist_pred and GROUND_TRUTH.get("waist"):
        k = GROUND_TRUTH["waist"] / waist_pred
        print(f"\nCalibrated on waist (k={k:.3f}):")
        cal_errs = []
        for name in ("chest", "hip", "thigh", "calf", "bicep", "forearm", "wrist"):
            pred = measurements.get(name)
            if pred is None:
                continue
            cal = pred * k
            truth = GROUND_TRUTH.get(name)
            if truth:
                cal_errs.append(abs(cal - truth))
                print(f"  {name:<9}{cal:>7.1f}  (truth {truth}, err {abs(cal-truth):.1f})")
            else:
                print(f"  {name:<9}{cal:>7.1f}")
        if cal_errs:
            print(f"  calibrated MAE (excl. waist anchor): {sum(cal_errs)/len(cal_errs):.2f} cm")


if __name__ == "__main__":
    from measurement.body_fat import estimate_weight_from_volume, bmi, navy_body_fat

    height = SUBJECT["height_cm"]
    true_weight = SUBJECT["weight_kg"]

    print(f"Running pipeline on {VIDEO} (height {height} cm)...")
    vertices, faces, measurements = run_pipeline(VIDEO)
    report(measurements)

    # Phase 4 check: weight estimated from mesh volume (no user weight).
    k = GROUND_TRUTH["waist"] / measurements["waist"]
    est_w = estimate_weight_from_volume(vertices, faces, area_correction=k * k)
    print(f"\nWeight from mesh volume (calibrated): {est_w} kg"
          + (f"   (true {true_weight})" if true_weight else ""))
    if true_weight:
        print(f"BMI from estimated weight: {bmi(est_w, height)}   (true {bmi(true_weight, height)})")

    # Phase 3 check: body fat on calibrated measurements.
    cal = {p: measurements[p] * k for p in ("waist", "hip", "neck")}
    print(f"Calibrated body fat: Navy {navy_body_fat(cal, height, SUBJECT['gender'])} %  |  "
          f"weight-based {measurements.get('body_fat_bmi_%')} %")
