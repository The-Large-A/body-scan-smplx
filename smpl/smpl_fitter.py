import torch
import smplx
import numpy as np
from config import SMPL_MODEL_PATH

device = torch.device("cpu")

# Torso body-height fractions (feet=0, head=1) sampled for the fit.
# Kept below the outstretched T-pose arms (~0.80) so the arms/head do not
# contaminate the torso width/depth targets.
TORSO_FRACTIONS = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def horizontal_extent_profile(mask, fractions):
    """
    From a boolean person-mask, measure the horizontal pixel extent at each
    requested body-height fraction (feet=0, head=1), plus the person's pixel
    height. Returns (widths_px: dict frac->pixels, pixel_height).
    """
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return {}, 0

    y_top, y_bot = ys.min(), ys.max()
    pixel_height = y_bot - y_top
    if pixel_height <= 0:
        return {}, 0

    band_px = max(1, int(0.01 * pixel_height))

    widths = {}
    for f in fractions:
        row = y_bot - f * pixel_height
        band = np.abs(ys - row) <= band_px
        if band.any():
            widths[f] = xs[band].max() - xs[band].min()

    return widths, pixel_height


class SMPLFitter:

    def __init__(self, gender="neutral"):

        self.model = smplx.create(
            model_path=SMPL_MODEL_PATH,
            model_type="smplx",
            gender=gender,
            num_betas=10,
            batch_size=1
        ).to(device)

    def fit(self, front_mask, side_mask, height_cm):
        """
        Fit SMPL-X shape (betas) + a global scale so the canonical mesh
        reproduces the torso width (front view) and depth (side view)
        profiles and the known standing height.
        """
        height_m = height_cm / 100.0

        # Silhouette -> real-world torso targets (metres).
        front_px, front_h = horizontal_extent_profile(front_mask, TORSO_FRACTIONS)
        side_px, side_h = horizontal_extent_profile(side_mask, TORSO_FRACTIONS)

        width_target = {f: (w * height_m / front_h) for f, w in front_px.items()}
        depth_target = {f: (d * height_m / side_h) for f, d in side_px.items()}

        betas = torch.zeros((1, 10), requires_grad=True, device=device)
        scale = torch.ones(1, requires_grad=True, device=device)

        body_pose = torch.zeros((1, 63), device=device)
        global_orient = torch.zeros((1, 3), device=device)

        optimizer = torch.optim.Adam([betas, scale], lr=0.02)

        for _ in range(500):

            optimizer.zero_grad()

            output = self.model(
                betas=betas,
                body_pose=body_pose,
                global_orient=global_orient
            )

            v = output.vertices[0]
            v = (v - v.mean(dim=0)) * scale

            y = v[:, 1]
            y_min = y.min()
            mesh_h = y.max() - y_min

            loss = 10.0 * (mesh_h - height_m) ** 2

            for f in TORSO_FRACTIONS:

                y_f = y_min + f * mesh_h
                band = torch.abs(y - y_f) < 0.02 * mesh_h

                if band.sum() < 10:
                    continue

                vb = v[band]

                if f in width_target:
                    w = vb[:, 0].max() - vb[:, 0].min()
                    loss = loss + (w - width_target[f]) ** 2

                if f in depth_target:
                    d = vb[:, 2].max() - vb[:, 2].min()
                    loss = loss + (d - depth_target[f]) ** 2

            # keep shape plausible
            loss = loss + 1e-4 * (betas ** 2).sum()

            loss.backward()
            optimizer.step()

        with torch.no_grad():

            output = self.model(
                betas=betas,
                body_pose=body_pose,
                global_orient=global_orient
            )

            v = output.vertices[0]
            v = (v - v.mean(dim=0)) * scale

        return v.cpu().numpy()
