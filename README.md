# Body Scan – Video-Based Body Measurement Estimation

## Overview

This project estimates human body measurements from a short video using computer vision and 3D body modeling.

It reconstructs a 3D human mesh using the SMPL-X model and computes body circumferences from cross-sectional slices of the mesh.

The system is designed as a foundation for applications in fitness tracking, health analytics, and digital body modeling.

---

## Features

- Video-based body measurement pipeline
- Pose estimation using MediaPipe (33 landmarks)
- Multi-frame pose averaging for stability
- SMPL-X 3D body reconstruction
- Height normalization for real-world scaling
- Measurement extraction using cross-sectional slicing
- Circumference estimation via ellipse fitting
- Debug visualization of mesh and measurement slices

---

## Measurements Supported

- Chest
- Waist
- Hip
- Thigh
- Calf
- Upper Arm
- Wrist

---

## Project Structure

```id="7p2i5k"
Body Scan/
│
├── pose/           # Pose estimation
├── smpl/           # SMPL-X fitting
├── measurement/    # Measurement logic
├── utils/          # Utilities
├── debug/          # Visualization tools
├── models/         # SMPL-X models (not included)
├── output/         # Generated results
│
├── main.py         # Entry point
├── config.py       # Configuration
├── requirements.txt
```

---

## Installation

Install dependencies:

```bash id="qlw6au"
pip install -r requirements.txt
```

---

## Setup

### 1. Download SMPL-X Model

Download SMPL-X from the official source and place it in:

```id="kq9q4m"
models/smplx/
```

Note: The model is not included due to licensing restrictions.

---

### 2. Prepare Input Video

Requirements:

- Full body visible
- Upright posture
- Slow rotation (preferably 360°)
- Minimal occlusion

---

## Usage

Run the program:

```bash id="zrm3qf"
python main.py your_video.mp4
```

---

## Output

Results are saved as:

```id="j0g9yo"
output/body_measurements.json
```

Example:

```json id="81w3a3"
{
  "chest": 98.2,
  "waist": 82.4,
  "hip": 101.1
}
```

---

## How It Works

1. Extract frames from input video
2. Detect body landmarks using MediaPipe
3. Average joints across frames
4. Fit SMPL-X body model
5. Scale mesh to real-world height
6. Extract cross-sectional slices
7. Fit ellipse to estimate circumference

---

## Limitations

- Accuracy depends on video quality and lighting
- Loose clothing can distort measurements
- Ellipse fitting may be inaccurate for irregular shapes
- Single-pose approximation limits precision

Typical error range: ±4–7 cm

---

## Future Improvements

- Convex hull-based circumference estimation
- Multi-frame mesh fusion
- Improved anatomical landmark detection
- Machine learning-based body measurement prediction
- Body fat estimation models

---

## Applications

- Fitness tracking
- Digital body measurement
- Online clothing sizing
- Health analytics
- Anthropometric studies

---

## License

This project depends on SMPL-X. Ensure compliance with its license when using model files.
