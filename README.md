# Body Scan – Video-Based Body Measurement & Composition

## Overview

Body Scan estimates human body **circumferences** and basic **body composition**
from a single short rotating video. It fits a 3D **SMPL-X** body model to the
person, measures the torso directly from the rotation silhouettes, measures the
limbs from the fitted mesh, and reports circumferences plus BMI, weight, and
body-fat estimates.

It runs **CPU-only** on an ordinary laptop, needs no depth sensor, reference
marker, or multi-camera rig — just one phone video and the person's height.

It is a **wellness / progress-tracking** tool, not a medical device.

---

## Current status at a glance

| | |
|---|---|
| **Input** | One monocular RGB video, 360° turn, ~10 s, known height |
| **Runtime** | CPU-only (MediaPipe + PyTorch/SMPL-X, ~1 min/scan) |
| **Calibrated accuracy** | **~2 cm mean absolute error** across all circumferences (validated, N=1) |
| **Uncalibrated accuracy** | ~15 % high but internally consistent (good for trend tracking) |
| **Latest validated MAE** | **1.99 cm** calibrated (down from 2.26 cm before the 2026-07 update) |
| **Validation** | `validate.py` against one subject with full tape ground truth |

> **Important caveat:** accuracy is validated on a **single subject (N=1)**.
> The numbers below are real and reproducible, but generalisation to other
> body types is **not yet proven** — see [Roadmap](#roadmap--future-work).

---

## Measurements produced

**Circumferences (cm):** neck, chest, waist, hip, bicep, forearm, wrist,
thigh, calf.

**Body composition:**
- **BMI** (from entered or estimated weight)
- **Weight** — entered by the user, or estimated from the fitted mesh volume
- **Body-fat %** — US-Navy tape method (needs no weight), with a weight-based
  Deurenberg cross-check when weight and age are supplied

Results print to the console, save to `output/body_measurements.json`, and (via
the CLI) can be inspected in an interactive 3D viewer.

---

## How it works

The pipeline turns one video into measurements in the following stages
(`pipeline.py` → `run_pipeline`).

### 1. Frame extraction
`utils/video_utils.py` samples every `FRAME_STEP`-th frame (default 5) from the
video, giving a set of frames spanning the full 360° turn.

### 2. Pose + silhouette per frame
`pose/pose_estimator.py` runs **MediaPipe Pose** (`model_complexity=2`,
`enable_segmentation=True`) on each frame, producing:
- **33 pose landmarks** (used for view selection and body-part heights)
- a **binary body silhouette mask**

The mask is then **morphologically opened + closed** (5×5 kernel) to remove
single-pixel spikes and holes that would otherwise corrupt the width readings.
*(This denoising was added in 2026-07 — it cut chest error from 3.3 → 2.9 cm.)*

### 3. View selection
`utils/view_selector.py` picks a **front** frame (maximum shoulder-landmark
pixel spread) and a **side** frame (minimum spread) across the whole spin. This
avoids trusting any single hand-labelled frame.

### 4. SMPL-X shape fit
`smpl/smpl_fitter.py` optimises the **10 SMPL-X shape coefficients (betas)** plus
a **global scale** (Adam, 500 iterations) so the canonical zero-pose mesh
reproduces:
- the **known standing height** (heavily weighted), and
- the **torso width profile** (from the front mask) and **depth profile**
  (from the side mask) at body-height fractions 0.45–0.70.

Torso fractions stay below the outstretched T-pose arms (~0.80) so arms/head do
not contaminate the torso targets. A small `β²` regulariser keeps the shape
plausible. The fitter also exposes the fitted **joint positions**, used for
limb slicing below.

### 5. Torso circumferences — measured directly from silhouettes
`measurement/body_measurements.py` measures chest/waist/hip **without trusting
the mesh**. For each body-height ratio (`HEIGHT_RATIOS`: chest 0.68, waist 0.58,
hip 0.50), it takes the horizontal silhouette extent in every frame, each
self-scaled by that frame's pixel height. Across a full rotation:
- the **90th-percentile** extent ≈ the true **frontal width**
- the **10th-percentile** extent ≈ the true **side depth**

An **ellipse** through those two axes (Ramanujan perimeter) gives the
circumference. Percentiles (not min/max) make this robust to a few bad frames.

*Why not the mesh?* SMPL-X's 10 betas cannot represent every torso cross-section
(e.g. a very flat abdomen), so direct silhouette measurement is more faithful
for the trunk.

### 6. Limb circumferences — from the fitted mesh
Each limb is isolated with a **vertex segmentation map**
(`models/smplx_vert_segmentation.json`, Meshcapade). The mesh is then sliced
**perpendicular to the limb's anatomical bone axis** — the vector between the
two bracketing SMPL-X joints (shoulder→elbow for the upper arm, knee→ankle for
the calf, etc.). Each slice's **convex-hull perimeter** is measured, and the
representative slice is taken per limb:

| Output | Segment | Slice |
|---|---|---|
| bicep | upper arm | thickest |
| forearm | forearm | thickest |
| wrist | forearm | thinnest |
| thigh | upper leg | thickest |
| calf | lower leg | thickest |
| neck | neck | median (PCA axis) |

Left and right are averaged.

*Why the bone axis?* PCA of a limb segment tilts when the limb has asymmetric
muscle bulk (deltoid, calf belly); an oblique cut yields an inflated elliptical
cross-section. Slicing along the true bone axis removes that inflation.
*(Added 2026-07 — it cut bicep error from 2.6 → 1.5 cm.)*

*Why convex hull?* A tape measure physically cannot dip into concavities, so the
convex hull of a cross-section is the **correct model of a tape measurement** —
this is a deliberate choice, not an approximation to "fix".

### 7. Per-user calibration (recommended)
Raw silhouette measurements are **shape-correct and repeatable** but run
uniformly ~15 % high (mask thickness + camera perspective). One reference
measurement removes this bias: the pipeline computes `k = real / measured` from a
single known part and scales **all** circumferences by `k`. Entered **once per
person**, not per video. See [Calibration](#calibration).

### 8. Body composition
`measurement/body_fat.py`:
- **Weight** — user-supplied, or `estimate_weight_from_volume` (watertight mesh
  volume × body density 1010 kg/m³, corrected by `k²` for the calibration).
- **BMI** — from weight + height.
- **Body-fat %** — US-Navy metric formula (waist/neck, plus hip for women).
- **Cross-check** — Deurenberg (BMI + age), when age is provided.

---

## Accuracy & validation

`validate.py` runs the full pipeline on a video with **known tape
measurements** (stored privately in `validation_data.py`, gitignored) and prints
predicted-vs-truth error per measurement and an overall MAE. This is the
objective gate used to accept or reject every change.

**Latest validated errors (single subject, calibrated on waist):**

| Measurement | Calibrated abs. error |
|---|---|
| chest | 2.9 cm |
| thigh | 1.3 cm |
| calf | 2.5 cm |
| bicep | 1.5 cm |
| forearm | 2.1 cm |
| wrist | 1.6 cm |
| **Mean (MAE)** | **1.99 cm** |

- **Weight from mesh volume:** within ~3–4 kg of the true weight.
- **Body-fat %:** method spread is inherent — Navy vs weight-based can differ
  several points; treat as approximate, watch the trend not the absolute.
- **Uncalibrated** values are ~15 % high but consistent, so **scan-to-scan
  trends remain reliable** even without calibration.

> Absolute values (truth/prediction) are intentionally **not reproduced here** —
> the README is public and the subject's real measurements are private. Only
> error magnitudes are shown.

---

## Development history

The project has gone through three major stages. Each accuracy change is gated
by `validate.py`.

### Stage 1 — Initial SMPL-X prototype (`0e6e75b`)
First end-to-end pipeline: MediaPipe + SMPL-X fit + naive cross-section
measurements. Established the approach but was inaccurate and cluttered.

### Stage 2 — Measurement pipeline overhaul (`f2d4b29`)
A ground-up rework driven by validation:
- **Torso** moved off the mesh to **direct silhouette measurement** (p90 width /
  p10 depth ellipse across the spin).
- Switched segmentation from MediaPipe **Selfie** to **Pose** (Selfie dropped
  frames, corrupting depth).
- **Limbs** measured from the fitted mesh via vertex segmentation.
- Added **per-user calibration**, **body composition** (Navy / BMI / Deurenberg
  / mesh-volume weight), a plain **Tkinter UI**, **clothing-size calibration**,
  metric/imperial units, and privacy isolation of validation data.
- Overall calibrated MAE reached **~2.3 cm**.

### Stage 3 — Accuracy refinement & cleanup (`e4ce49b`, 2026-07)
A research gauntlet over external projects plus a code audit:
- **Adopted:** bone-axis limb slicing (bicep 2.6 → 1.5 cm) and mask
  morphological denoising (chest 3.3 → 2.9 cm). **Calibrated MAE 2.26 → 1.99 cm.**
- **Removed** dead code and fixed a clean-clone crash (the optional 3D viewer is
  now a lazy import).

---

## What we've tried and rejected

Every idea below was implemented and measured against `validate.py`, then
**cut because it did not improve (or actively hurt) accuracy**. Recorded so the
same ground isn't re-tilled.

### Architectural pivots (Stage 2)
| Tried | Outcome | Resolution |
|---|---|---|
| Fit SMPL-X directly to silhouettes for the torso | MAE worse; 10 betas can't represent a flat torso | Direct silhouette ellipse measurement |
| MediaPipe **Selfie** segmentation | Mask dropouts corrupted side depth | MediaPipe **Pose** segmentation |
| Single "side" frame for depth | Not exactly 90° → inflated depth | Min extent across the **full spin** |
| `smooth_vertices` mesh smoothing | Averaged vertices by array index, scrambling the mesh (bicep read 116 cm) | Removed entirely |
| Neck = thinnest slice | Bad edge slice near the jaw (too small) | **Median** slice |

### Research gauntlet (Stage 3, 5 external repos)
Sources studied: SMPL-Anthropometry, SMPL-Fitting, Body-Shape-Estimation,
arvkr/BodyScan, ankesh007/Body-Measurement-CV. Most are **3D-scan or
marker/GPU-dependent** pipelines whose data machinery does not transfer to
monocular silhouettes. Ideas that did transfer were tested:

| Idea | Result | Verdict |
|---|---|---|
| **Bone-axis limb slicing** | MAE 2.26 → **2.06** | ✅ **adopted** |
| **Mask morphological denoising** | 2.06 → **1.99** | ✅ **adopted** |
| Robust (Huber) fit loss | 2.26 → 2.43 (worse) | ❌ only 6 clean torso targets, no outliers to reject |
| Staged (coarse-to-fine) loss weighting | 2.26 → 2.39 (worse) | ❌ perturbs an already-good fit |
| Learning-rate decay | 2.26 → 2.26 (no-op) | ❌ fit converges long before decay |
| 2D landmark reprojection (shoulder:hip) | 2.06 → 3.66 (much worse) | ❌ MediaPipe shoulder = acromion, SMPL-X joint = glenohumeral; matching them collapses the arms |
| Pose-init from landmarks | limb girth Δ < 0.4 cm under pose change | ❌ measurements are pose-invariant after bone-axis slicing; no benefit |

**Key finding:** the SMPL-X **fit is not the accuracy bottleneck** — it already
sits at a good optimum, and objective tweaks (robust loss, staging, LR decay)
only perturb it. Accuracy gains live in the **measurement geometry**, not the
fit.

---

## Known limitations

- **Single-subject validation (N=1).** Absolute accuracy on other body types is
  unproven.
- **Calibration dependency.** Without a one-time calibration, values are ~15 %
  high (though internally consistent).
- **No camera model.** The ~15 % bias is largely perspective/focal-length; the
  pipeline currently absorbs it with calibration rather than correcting it.
- **Chest in a strict T-pose** is the hardest measurement (arms partly occlude
  the chest line).
- **Loose clothing, cluttered backgrounds, heavy perspective** all reduce
  accuracy.
- Single-camera reconstruction — **not a medical measurement.**

---

## Roadmap / future work

Ordered roughly by expected impact.

1. **Multi-person validation.** Collect tape ground truth for a handful of
   additional subjects to (a) confirm the method generalises and (b) test
   whether a single **global calibration factor** can replace per-user
   calibration. *This is the top priority — everything else is speculative until
   N > 1.*
2. **Perspective / camera correction.** Estimate focal length / subject distance
   (or add a lightweight calibration step) to remove the ~15 % systematic bias
   at its source and reduce or eliminate the need for per-user calibration. This
   is the biggest lever on *absolute* accuracy.
3. **Expand size charts.** Only *women's jeans → hip* exists today
   (`sizing.py`). Add men's and other garments for easier calibration.
4. **Deferred fit ideas** (only if a concrete need appears): a differentiable
   silhouette-IoU fitting term (needs a 2D renderer), or per-frame pose fitting
   (needs a landmark→SMPL-X IK step) — the latter only matters for
   pose-dependent measures, which the current bone-axis method sidesteps.

**Contributing an accuracy change:** implement it, run `python validate.py`
before and after, and **keep it only if MAE drops.** Add a row to
[What we've tried and rejected](#what-weve-tried-and-rejected) either way.

---

## Calibration

Two ways to provide the one-time reference:

- **Clothing size (easy):** pick a known size from a chart (e.g. women's jeans →
  hip). The size's midpoint circumference is the anchor. Approximate (vanity
  sizing varies) but far better than nothing.
- **Tape measurement (most accurate):** set `CALIBRATION_PART` and
  `CALIBRATION_CM` in `config.py` to one real measured circumference.

Without calibration, absolute values are ~15 % high but **trends between scans
stay reliable**.

---

## Project structure

```
Body Scan/
├── pose/            # MediaPipe pose + segmentation (+ mask denoising)
├── smpl/            # SMPL-X shape fitting (betas + scale; exposes joints)
├── measurement/     # torso, limb (bone-axis), and body-composition logic
├── utils/           # video / json / view-selection helpers
├── debug/           # optional 3D visualization (dev-only, not distributed)
├── models/          # SMPL-X models + vertex segmentation (not distributed)
├── output/          # generated JSON results
│
├── pipeline.py      # shared scan pipeline (video -> measurements)
├── main.py          # CLI entry point (+ optional 3D viewer)
├── ui.py            # plain Tkinter GUI
├── validate.py      # accuracy check against known tape measurements
├── sizing.py        # clothing size charts for calibration
├── config.py        # configuration
└── requirements.txt
```

Private/local-only (gitignored): `models/`, `videos/`, `output/`, `debug/`,
`validation_data.py`.

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
4. *(For validation only)* copy `validation_data.example.py` to
   `validation_data.py` and fill in a subject's video path, stats, and tape
   measurements.

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
Results are written to `output/body_measurements.json`. A 3D viewer opens if the
optional `debug/` tools are present.

**Validate accuracy** (against known tape measurements):
```bash
python validate.py
```

---

## Configuration reference (`config.py`)

| Setting | Meaning |
|---|---|
| `FRAME_STEP` | Sample every Nth video frame (default 5) |
| `USER_HEIGHT_CM` | Subject height — the absolute scale anchor (**required**) |
| `GENDER` | `"male"`, `"female"`, or `"neutral"` (selects SMPL-X model) |
| `USER_WEIGHT_KG` | Optional; if `None`, weight is estimated from mesh volume |
| `USER_AGE` | Optional; enables the Deurenberg body-fat cross-check |
| `UNIT_SYSTEM` | `"metric"` or `"imperial"` (UI display only) |
| `CALIBRATION_PART` / `CALIBRATION_CM` | One real measured part for per-user calibration |
| `HEIGHT_RATIOS` | Body-height fractions for chest/waist/hip silhouette slices |

---

## License

Depends on SMPL-X — ensure compliance with its licence when using model files.
```
