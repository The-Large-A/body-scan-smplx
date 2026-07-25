import mediapipe as mp
import numpy as np
import cv2

mp_pose = mp.solutions.pose

class PoseEstimator:

    def __init__(self):

        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=True
        )

    def detect(self, frame):

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        pose_results = self.pose.process(image)

        if not pose_results.pose_landmarks:
            return None, None

        mask = (pose_results.segmentation_mask > 0.5).astype(np.uint8)
        # Open+close removes single-pixel silhouette spikes/holes that would
        # otherwise inflate the p90 width used for torso extents.
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel).astype(bool)

        joints = []

        for lm in pose_results.pose_landmarks.landmark:
            joints.append([lm.x, lm.y, lm.z])

        return np.array(joints), mask