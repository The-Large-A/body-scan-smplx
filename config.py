FRAME_STEP = 5

USER_HEIGHT_CM = 170  # placeholder; set to the user's real height (cm)

GENDER = "neutral"  # "male", "female", or "neutral"

USER_WEIGHT_KG = None   # optional; if None, weight is estimated from mesh volume
USER_AGE = None         # optional; enables the weight-based body-fat cross-check

UNIT_SYSTEM = "metric"  # "metric" or "imperial" (UI display only)

# Optional one-time per-user calibration to remove the systematic silhouette
# bias. Measure ONE body part with a tape and set both values; the pipeline
# scales all circumference outputs by (real / measured). Leave as None to skip.
CALIBRATION_PART = None   # e.g. "waist"
CALIBRATION_CM = None      # e.g. 90

HEIGHT_RATIOS = {
    "chest": 0.68,
    "waist": 0.58,
    "hip": 0.50,
    "thigh": 0.32,
    "calf": 0.20
}

SMPL_MODEL_PATH = "models"
OUTPUT_FILE = "output/body_measurements.json"