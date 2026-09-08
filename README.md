# sch_thesis

GitHub 계정 `parkhookjung-debug`의 프로젝트 파일들을 한 저장소 안에 정리한 모음입니다.

이 저장소는 기존 프로젝트의 Git 히스토리를 합친 것이 아니라, 각 저장소의 현재 파일 스냅샷을 `projects/` 아래에 폴더별로 정리한 형태입니다.

## Folder Structure

```text
projects/
  bjj-training-system/
  boxing/
  boxing-coach/
  boxing-game/
  boxing-punch-pipeline/
  Chungnam_Competition/
  chungnam-weather-tour/
  chungnam-welfare-crawler/
  imageclef2026-deepfake/
  Reelmong/
  reelmong-algorithm/
  Weather-RC/
```

## Source Repositories

| Folder | Original repository | Visibility | Main language | Notes |
| --- | --- | --- | --- | --- |
| `projects/bjj-training-system` | `parkhookjung-debug/bjj-training-system` | public | Python | BJJ personal training system |
| `projects/boxing` | `parkhookjung-debug/boxing` | public | Python | Boxing project files |
| `projects/boxing-coach` | `parkhookjung-debug/boxing-coach` | public | Python | Boxing coach app |
| `projects/boxing-game` | `parkhookjung-debug/boxing-game` | public | TypeScript | Boxing game |
| `projects/boxing-punch-pipeline` | `parkhookjung-debug/boxing-punch-pipeline` | public | Python | Pose extraction, ST-GCN training, realtime coach pipeline |
| `projects/Chungnam_Competition` | `parkhookjung-debug/Chungnam_Competition` | public | Python | Chungnam tour pass AI recommendation service |
| `projects/chungnam-weather-tour` | `parkhookjung-debug/chungnam-weather-tour` | public | TypeScript | Weather and tour recommendation project |
| `projects/chungnam-welfare-crawler` | `parkhookjung-debug/chungnam-welfare-crawler` | private | Python | Chungnam welfare crawler |
| `projects/imageclef2026-deepfake` | `parkhookjung-debug/imageclef2026-deepfake` | public | Jupyter Notebook | ImageCLEF 2026 deepfake project |
| `projects/Reelmong` | `parkhookjung-debug/Reelmong` | public | Python | Reelmong project |
| `projects/reelmong-algorithm` | `parkhookjung-debug/reelmong-algorithm` | public | Python | Reelmong recommendation/viral algorithm |
| `projects/Weather-RC` | `parkhookjung-debug/Weather-RC` | public | none detected | Empty source repository at import time |

## Import Notes

- The new repository is private because it includes files from a private source repository.
- `.git` directories from the original repositories were intentionally excluded.
- The contents are a snapshot of the default branch from each source repository at import time.
- Large project assets such as videos, notebooks, models, and documents are preserved when they were already tracked in the source repositories.
