COCO_POSE_LANDMARKS = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

NUM_JOINTS = len(COCO_POSE_LANDMARKS)

LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12

SELF_LINKS = [(i, i) for i in range(NUM_JOINTS)]

SKELETON_EDGES = [
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
]

CLASS_NAMES = [
    "none",
    "jab",
    "cross",
    "hook",
    "uppercut",
]


def landmark_columns():
    columns = []
    for idx in range(NUM_JOINTS):
        columns.extend(
            [
                f"kpt_{idx}_x",
                f"kpt_{idx}_y",
                f"kpt_{idx}_score",
            ]
        )
    return columns
