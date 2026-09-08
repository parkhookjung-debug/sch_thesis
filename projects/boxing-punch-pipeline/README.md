# Boxing Punch Pipeline

Research-grade video -> RTMPose raw pose CSV -> preprocessed NPZ -> ST-GCN training.

## 1. Install

Use Python **3.10 or 3.11** for the MMPose/OpenMMLab stack. Python 3.14 is too new
for this dependency set on Windows and will fall back to source builds.

```powershell
cd D:\Code\boxing-punch-pipeline
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
mim install "mmcv>=2.0.0"
python -m pip install "mmdet>=3.0.0" "mmpose>=1.3.0"
```

The project pins `torch==2.1.2` / `torchvision==0.16.2` because OpenMMLab wheels
are version-specific. Letting pip install the newest PyTorch can force `mmcv` into
a slow source build on Windows.

If `python --version` shows `3.14`, create the virtual environment with a separate
Python 3.10 or 3.11 install instead. For example:

```powershell
C:\Path\To\Python311\python.exe -m venv .venv
```

This pipeline uses **MMPose RTMPose** for pose extraction. That is the research-facing
default. MediaPipe is intentionally not used as the main extractor.

## 2. Put Videos Here

Copy training videos into:

```text
videos/
```

Supported by OpenCV: `.mp4`, `.mov`, `.avi`, `.mkv`.

## 3. Extract Raw Pose CSV

```powershell
python scripts\extract_pose.py --input videos --output data\raw --pose2d human
```

Output example:

```text
data/raw/my_video.pose.csv
```

The raw CSV keeps one row per video frame and 17 COCO body landmarks from RTMPose.

## 4. Label Punch Segments

Create or edit:

```text
data/labels/labels.csv
```

Format:

```csv
video_id,start_frame,end_frame,label
my_video,120,145,jab
my_video,230,260,cross
```

Recommended labels:

```text
none, jab, cross, lead_hook, rear_hook, lead_uppercut, rear_uppercut
```

## 5. Build NPZ Dataset

```powershell
python scripts\preprocess_dataset.py --raw-dir data\raw --labels data\labels\labels.csv --output data\processed\boxing_punch_dataset.npz
```

Output arrays:

```text
X: (N, C, T, V)
y: (N,)
classes: class names
meta: video/window metadata
```

Default:

```text
C = 3  -> x, y, confidence
T = 64 -> 64-frame window
V = 17 -> COCO body landmarks
```

## 6. Train ST-GCN

```powershell
python scripts\train_stgcn.py --data data\processed\boxing_punch_dataset.npz --epochs 50
```

Checkpoints are saved to:

```text
models/
```

## Notes

- The model learns punch motion from a sliding time window, not from a single pose.
- Preprocessing centers the body at the hips and scales by shoulder/hip size.
- The default extractor is MMPose `pose2d=human`, which maps to RTMPose-m in current MMPose docs.
- For better results, label the full punch segment: start -> extension/contact -> recovery.
- If your stance switches often, keep `lead_*` and `rear_*` labels. If not, merge them into `hook` and `uppercut` first.
