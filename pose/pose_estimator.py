import mediapipe as mp
import numpy as np
import cv2

mp_pose = mp.solutions.pose
mp_selfie = mp.solutions.selfie_segmentation

class PoseEstimator:

    def __init__(self):

        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False
        )

        self.segment = mp_selfie.SelfieSegmentation(model_selection=1)

    def detect(self, frame):

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        pose_results = self.pose.process(image)

        seg_results = self.segment.process(image)

        mask = seg_results.segmentation_mask > 0.5

        if not pose_results.pose_landmarks:
            return None, mask

        joints = []

        for lm in pose_results.pose_landmarks.landmark:
            joints.append([lm.x, lm.y, lm.z])

        return np.array(joints), mask