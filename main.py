import sys

from utils.video_utils import extract_frames
from pose.pose_estimator import PoseEstimator
from smpl.smpl_fitter import SMPLFitter
from measurement.body_measurements import compute_measurements
from utils.json_utils import save_measurements
from utils.view_selector import select_views

from config import FRAME_STEP, OUTPUT_FILE

from debug.visualize_mesh import visualize_mesh
from debug.visualize_slices import visualize_slice
from debug.visualize_measurements import visualize_measurements
from config import HEIGHT_RATIOS


def main(video_path):

    print("Extracting frames...")

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
        print("Not enough frames detected")
        return

    joints_views = select_views(joints_all)

    print("Fitting SMPL-X model...")

    fitter = SMPLFitter()

    vertices = fitter.fit(joints_views, masks)

    print("Opening 3D body viewer with measurement rings...")

    visualize_measurements(
        vertices,
        fitter.model.faces
    )

    #print("Showing measurement slices...")
#
    #for part,ratio in HEIGHT_RATIOS.items():
    #    visualize_slice(vertices, ratio)

    print("Computing body measurements...")

    measurements = compute_measurements(vertices)

    measurements = {k: float(v) for k,v in measurements.items()}

    for k,v in measurements.items():
        print(k,":",round(v,2),"cm")

    save_measurements(measurements, video_path, OUTPUT_FILE)

    print("Mesh height (m):", vertices[:,1].max() - vertices[:,1].min())


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print("Usage: python main.py <video>")
        exit()

    main(sys.argv[1])