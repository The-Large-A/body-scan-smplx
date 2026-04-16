import json
from datetime import datetime
import os

def save_measurements(measurements, video_path, output_file):

    os.makedirs("output", exist_ok=True)

    data = {
        "timestamp": datetime.now().isoformat(),
        "video_source": video_path,
        "measurements": measurements
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)

    print("Results saved to", output_file)