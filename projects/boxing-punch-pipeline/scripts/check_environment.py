from __future__ import annotations

import platform
import sys


def try_import(name: str) -> str | None:
    try:
        __import__(name)
    except Exception as exc:
        return repr(exc)
    return None


def main() -> None:
    print(f"python={sys.version.split()[0]}")
    print(f"platform={platform.platform()}")

    major, minor = sys.version_info[:2]
    if (major, minor) not in {(3, 10), (3, 11)}:
        print("status=bad")
        print("reason=MMPose/OpenMMLab on Windows should use Python 3.10 or 3.11.")
        raise SystemExit(1)

    required = ["torch", "cv2", "mmcv", "mmdet", "mmpose"]
    failures = {name: err for name in required if (err := try_import(name))}
    if failures:
        print("status=incomplete")
        for name, error in failures.items():
            print(f"{name}={error}")
        raise SystemExit(2)

    try:
        from mmpose.apis import MMPoseInferencer  # noqa: F401
    except Exception as exc:
        print("status=incomplete")
        print(f"MMPoseInferencer={exc!r}")
        raise SystemExit(2)

    print("status=ok")


if __name__ == "__main__":
    main()
