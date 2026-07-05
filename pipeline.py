"""Core scan pipeline shared by the CLI, validator, and UI (no visualization)."""

import config
from config import FRAME_STEP

from utils.video_utils import extract_frames
from pose.pose_estimator import PoseEstimator
from smpl.smpl_fitter import SMPLFitter
from measurement.body_measurements import compute_measurements
from utils.view_selector import select_views


def run_pipeline(video_path):
    """Video -> (vertices, faces, measurements). Reads settings from config."""
    frames = extract_frames(video_path, FRAME_STEP)

    pose = PoseEstimator()

    joints_all = []
    masks = []

    for frame in frames:
        joints, mask = pose.detect(frame)
        if joints is not None:
            joints_all.append(joints)
            masks.append(mask)

    if len(joints_all) < 3:
        raise RuntimeError("Not enough frames with a detected person.")

    front_idx, side_idx = select_views(joints_all)

    fitter = SMPLFitter(gender=config.GENDER)
    vertices = fitter.fit(masks[front_idx], masks[side_idx], config.USER_HEIGHT_CM)

    measurements = compute_measurements(vertices, masks, fitter.model.faces)

    return vertices, fitter.model.faces, measurements
