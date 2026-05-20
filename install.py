import subprocess
import sys
import importlib
import importlib.util


def _installed(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None


def _pip(*args: str) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps", "-q", *args])


def ensure_deps() -> None:
    if not _installed("fairseq"):
        print("[install] Instalando fairseq...", flush=True)
        _pip("fairseq==0.12.2")
        importlib.invalidate_caches()

    if not _installed("rvc_python"):
        print("[install] Instalando rvc-python...", flush=True)
        _pip("rvc-python==0.1.5")
        importlib.invalidate_caches()
