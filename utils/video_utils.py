import cv2


def extract_frames(video_path, step=5):

    cap = cv2.VideoCapture(video_path)

    frames = []
    i = 0

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            break

        if i % step == 0:
            frames.append(frame)

        i += 1

    cap.release()

    return frames