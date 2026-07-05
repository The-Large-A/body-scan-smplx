# Body Scan – Video-Based Body Measurement & Composition

## Overview

Body Scan estimates human body measurements and basic body composition from a
short rotating video. It fits a 3D SMPL-X body model to the person, measures
the torso directly from the rotation silhouettes, measures the limbs from the
fitted mesh, and reports circumferences plus BMI and body-fat estimates.

It is a **wellness / progress-tracking** tool, not a medical device.

---

## Measurements

**Circumferences:** neck, chest, waist, hip, bicep, forearm, wrist, thigh, calf

**Body composition:** BMI, weight (entered or estimated from mesh volume),
body-fat % (US-Navy tape method, plus a weight-based Deurenberg cross-check
when weight and age are provided)

---

## How it works

1. Extract frames from the rotating video.
2. Detect pose landmarks and a body silhouette per frame (MediaPipe Pose).
3. **Torso (chest / waist / hip):** measured directly from the silhouettes.
   Across the full spin, the widest on-screen body width is the true frontal
   width and the narrowest is the true side depth; an ellipse through the two
   gives the circumference. This avoids trusting any single "front"/"side"
   frame.
4. Fit SMPL-X shape to the silhouette + known height (gendered model).
5. **Limbs (bicep / forearm / wrist / thigh / calf / neck):** isolate each part
   with a vertex segmentation map, find its long axis (PCA), slice
   perpendicular, and measure the perimeter.
6. Optionally apply a one-time per-user calibration (see below).
7. Compute BMI and body-fat.

---

## Calibration (recommended)

Raw silhouette measurements are **shape-correct and repeatable** but run
uniformly ~15% high (mask thickness + camera perspective). A single reference
measurement removes this bias for a person; it is entered **once per person**,
not per video, and every later scan of that person stays accurate.

Two ways to provide it:

- **Clothing size (easy):** pick a known size from a chart (e.g. women's jeans
  → hip). The size's midpoint circumference is used as the anchor. Approximate
  (vanity sizing varies) but far better than no calibration.
- **Tape measurement (most accurate):** set `CALIBRATION_PART` and
  `CALIBRATION_CM` in `config.py` to one real measured circumference.

Without calibration, absolute values are ~15% high but **trends between scans
are still reliable**.

---

## Project structure

```
Body Scan/
├── pose/            # MediaPipe pose + segmentation
├── smpl/            # SMPL-X shape fitting
├── measurement/     # torso, limb, and body-composition logic
├── utils/           # video / json / view-selection helpers
├── debug/           # 3D visualization tools
├── models/          # SMPL-X models + vertex segmentation (not distributed)
├── output/          # generated JSON results
│
├── pipeline.py      # shared scan pipeline (video -> measurements)
├── main.py          # CLI entry point (+ 3D viewer)
├── ui.py            # plain Tkinter GUI
├── validate.py      # accuracy check against known tape measurements
├── sizing.py        # clothing size charts for calibration
├── config.py        # configuration
└── requirements.txt
```

---

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place SMPL-X models in `models/smplx/` (`SMPLX_MALE.npz`,
   `SMPLX_FEMALE.npz`, `SMPLX_NEUTRAL.npz`). Not distributed — obtain from the
   official SMPL-X source under its licence.
3. Place the SMPL-X vertex segmentation map at
   `models/smplx_vert_segmentation.json` (Meshcapade SMPL-X body segmentation).

---

## Recording guidance

- Full body in frame the whole time; camera still (tripod), person rotates.
- One smooth, steady 360° turn (~10 s).
- **T-pose** (arms out) so limbs separate from the torso; tight clothing.
- Film from ~3 m back to reduce perspective distortion.

---

## Usage

**GUI (recommended):**
```bash
python ui.py
```
Pick a video, enter height (weight/age/gender optional), optionally pick a
clothing size to calibrate, press **Scan**. The Settings tab switches to
imperial units.

**CLI:**
```bash
python main.py videos/your_video.mp4
```
Set height, gender, and optional weight/age/calibration in `config.py` first.
Results are written to `output/body_measurements.json`.

**Validate accuracy** (against known tape measurements):
```bash
python validate.py
```

---

## Accuracy

Validated against a subject with known tape measurements:

- **Calibrated:** mean absolute error ~2 cm across all circumferences;
  weight-from-volume within ~3 kg.
- **Uncalibrated:** ~15% high but consistent (good for trend tracking).

Body-fat estimates carry inherent method spread (Navy vs. weight-based can
differ several %) and should be treated as approximate.

---

## Limitations

- Absolute accuracy depends on calibration; without it, values are biased high.
- Chest is the hardest measurement in a strict T-pose (arms occlude it).
- Loose clothing, cluttered backgrounds, and heavy perspective reduce accuracy.
- Single-camera reconstruction; not a medical measurement.

---

## License

Depends on SMPL-X — ensure compliance with its licence when using model files.
```
