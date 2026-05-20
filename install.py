import subprocess
import sys
import importlib
import importlib.util
import os

VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")


def _ensure_path() -> None:
    if VENDOR not in sys.path:
        sys.path.insert(0, VENDOR)


def _installed(pkg: str) -> bool:
    _ensure_path()
    return importlib.util.find_spec(pkg) is not None


def _pip(*args: str) -> None:
    os.makedirs(VENDOR, exist_ok=True)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--no-deps", "-q", "--target", VENDOR, *args
    ])
    _ensure_path()
    importlib.invalidate_caches()


def ensure_deps() -> None:
    _ensure_path()
    if not _installed("fairseq"):
        print("[install] Instalando fairseq...", flush=True)
        _pip("fairseq==0.12.2")
    if not _installed("rvc_python"):
        print("[install] Instalando rvc-python...", flush=True)
        _pip("rvc-python==0.1.5")
