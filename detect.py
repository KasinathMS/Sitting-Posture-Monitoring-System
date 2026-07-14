import cv2
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

video = cv2.VideoCapture("Video.mp4")

NECK_THRESHOLD  = 22   
TORSO_LOW       = 5    
TORSO_HIGH      = 8     

frame_count = 0
WARMUP_FRAMES = 5

# memory variable
last_status = "UPRIGHT"

GREEN  = (0, 200, 0)
RED    = (0, 0, 255)
YELLOW = (0, 255, 255)
ORANGE = (0, 165, 255)
BLUE   = (255, 0, 0)


def calculate_angle(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)

    radians = (np.arctan2(c[1] - b[1], c[0] - b[0]) -
               np.arctan2(a[1] - b[1], a[0] - b[0]))

    angle = np.abs(np.degrees(radians))
    if angle > 180:
        angle = 360 - angle

    return angle


def get_dominant_side(landmarks):
    left_vis  = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility
    right_vis = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility
    return "LEFT" if left_vis >= right_vis else "RIGHT"


while True:
    success, img = video.read()
    if not success:
        break

    img = cv2.resize(img, (800, 600))
    h, w, _ = img.shape

    result = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if not result.pose_landmarks:
        cv2.imshow("Sitting Posture Monitor", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    landmarks = result.pose_landmarks.landmark
    side = get_dominant_side(landmarks)

    if side == "LEFT":
        idx_shoulder = mp_pose.PoseLandmark.LEFT_SHOULDER.value
        idx_ear      = mp_pose.PoseLandmark.LEFT_EAR.value
        idx_hip      = mp_pose.PoseLandmark.LEFT_HIP.value
    else:
        idx_shoulder = mp_pose.PoseLandmark.RIGHT_SHOULDER.value
        idx_ear      = mp_pose.PoseLandmark.RIGHT_EAR.value
        idx_hip      = mp_pose.PoseLandmark.RIGHT_HIP.value

    shoulder = [landmarks[idx_shoulder].x * w, landmarks[idx_shoulder].y * h]
    ear      = [landmarks[idx_ear].x * w,      landmarks[idx_ear].y * h]
    hip      = [landmarks[idx_hip].x * w,      landmarks[idx_hip].y * h]

    shoulder_pt = tuple(np.array(shoulder).astype(int))
    ear_pt      = tuple(np.array(ear).astype(int))
    hip_pt      = tuple(np.array(hip).astype(int))

    # NECK
    vertical_above_shoulder = [shoulder[0], shoulder[1] - 100]
    neck_angle = calculate_angle(vertical_above_shoulder, shoulder, ear)

    neck_status = "FORWARD HEAD" if neck_angle >= NECK_THRESHOLD else "GOOD"
    neck_color  = RED if neck_status == "FORWARD HEAD" else GREEN

    # TORSO
    vertical_above_hip = [hip[0], hip[1] - 100]
    torso_angle = calculate_angle(vertical_above_hip, hip, shoulder)

    frame_count += 1

    if frame_count < WARMUP_FRAMES:
        overall_posture = "CALIBRATING..."
        overall_color   = YELLOW

        slouch_status = "UPRIGHT"
        slouch_color  = GREEN

    else:
                
        if torso_angle < TORSO_LOW:
            slouch_status = "SLOUCHING"

        elif torso_angle > TORSO_HIGH:
            slouch_status = "UPRIGHT"

        else:
            slouch_status = last_status

        # update memory
        last_status = slouch_status

        slouch_color = RED if slouch_status == "SLOUCHING" else GREEN

        bad_count = sum([
            neck_status == "FORWARD HEAD",
            slouch_status == "SLOUCHING",
        ])

        if bad_count == 0:
            overall_posture = "EXCELLENT POSTURE"
            overall_color   = GREEN
        elif bad_count == 1:
            overall_posture = "FAIR POSTURE"
            overall_color   = ORANGE
        else:
            overall_posture = "POOR POSTURE"
            overall_color   = RED

    # DRAW
    cv2.line(img, shoulder_pt, ear_pt, neck_color, 3)
    cv2.line(img, hip_pt, shoulder_pt, slouch_color, 3)

    cv2.line(img, shoulder_pt, (shoulder_pt[0], shoulder_pt[1] - 80), BLUE, 1)
    cv2.line(img, hip_pt, (hip_pt[0], hip_pt[1] - 80), BLUE, 1)

    for pt in [ear_pt, shoulder_pt, hip_pt]:
        cv2.circle(img, pt, 6, YELLOW, -1)

    # TEXT
    cv2.putText(img, overall_posture,
                (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.95, overall_color, 2)

    cv2.putText(img, f"Neck : {neck_status} ({neck_angle:.1f} deg)",
                (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.65, neck_color, 2)

    cv2.putText(img, f"Torso: {slouch_status} ({torso_angle:.2f} deg)",
                (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, slouch_color, 2)

    if frame_count >= WARMUP_FRAMES:
        if neck_status == "FORWARD HEAD" and slouch_status == "SLOUCHING":
            cv2.putText(img, "FIX YOUR POSTURE!",
                        (w//2 - 160, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, RED, 3)

    cv2.imshow("Sitting Posture Monitor", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()