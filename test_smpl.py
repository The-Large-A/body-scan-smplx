import smplx
import mediapipe as mp


model = smplx.create(
    model_path="models",
    model_type="smplx",
    gender="neutral"
)

print(mp.__version__)
print(mp.solutions.pose)

print("SMPL model loaded successfully")