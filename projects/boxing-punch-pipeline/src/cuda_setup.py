"""Make onnxruntime-gpu see the CUDA DLLs that PyTorch ships with itself.

PyTorch 2.11+cu128 bundles its own copy of cuBLAS, cuDNN, cuFFT in
``torch/lib`` (cublasLt64_12.dll, cudnn64_9.dll, ...). onnxruntime-gpu looks
for those on PATH and falls back to CPU silently when it can't find them,
which is exactly what happened in this project — pose extraction looked
fast on a synthetic frame because most of the work was done on CPU.

Importing this module BEFORE importing onnxruntime / rtmlib fixes that.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


_REGISTERED: list[Path] = []


def register_torch_cuda_dlls() -> list[Path]:
    """Add torch's bundled lib directory to the Windows DLL search path."""
    if _REGISTERED:
        return _REGISTERED
    if sys.platform != "win32":
        return []
    try:
        import torch  # noqa: F401
    except ImportError:
        return []
    torch_lib = Path(os.path.dirname(__file__)).parent / ".venv-gpu" / "Lib" / "site-packages" / "torch" / "lib"
    if not torch_lib.exists():
        # fall back to introspection
        import torch
        torch_lib = Path(torch.__file__).parent / "lib"
    if not torch_lib.exists():
        return []
    os.add_dll_directory(str(torch_lib))
    # also prepend to PATH so child processes inherit it
    os.environ["PATH"] = str(torch_lib) + os.pathsep + os.environ.get("PATH", "")
    _REGISTERED.append(torch_lib)
    return _REGISTERED


# Run on import — this module is meant to be a one-line hook.
register_torch_cuda_dlls()
