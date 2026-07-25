import sys

from pipeline import run_pipeline
from utils.json_utils import save_measurements
from config import OUTPUT_FILE


def main(video_path):

    print("Running scan pipeline...")

    vertices, faces, measurements = run_pipeline(video_path)

    # Optional 3D preview. Lives in debug/ (dev-only, not distributed), so
    # skip it gracefully when that folder isn't present.
    try:
        from debug.visualize_measurements import visualize_measurements
        print("Opening 3D body viewer with measurement rings...")
        visualize_measurements(vertices, faces)
    except ImportError:
        print("3D viewer unavailable (debug/ not present); skipping preview.")

    measurements = {k: float(v) for k, v in measurements.items()}

    for k, v in measurements.items():
        print(k, ":", round(v, 2))

    save_measurements(measurements, video_path, OUTPUT_FILE)

    print("Mesh height (m):", vertices[:, 1].max() - vertices[:, 1].min())


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print("Usage: python main.py <video>")
        exit()

    main(sys.argv[1])
