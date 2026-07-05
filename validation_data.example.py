"""
Template for validation data.

Copy this file to validation_data.py (which is gitignored) and fill in a real
subject's video path, stats, and tape measurements. validate.py reads it.
"""

SUBJECT = {
    "video": "videos/your_video.mp4",
    "height_cm": 170,
    "weight_kg": None,   # optional
    "age": None,         # optional
    "gender": "neutral",  # "male", "female", or "neutral"
    "ground_truth": {    # tape measurements, cm
        "chest": 0,
        "waist": 0,
        "thigh": 0,
        "calf": 0,
        "bicep": 0,
        "forearm": 0,
        "wrist": 0,
    },
}
