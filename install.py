# Gestor de dependencias en tiempo de ejecución.
# Instala fairseq y rvc-python en una carpeta local (vendor/) si no están disponibles,
# para que la app funcione en entornos donde no se puede modificar el entorno global de Python.
import subprocess
import sys
import importlib
import importlib.util
import os

# vendor/ vive junto a este archivo; se agrega al sys.path para que Python
# pueda importar los paquetes instalados ahí como si fueran del entorno global.
VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")


def _ensure_path() -> None:
    if VENDOR not in sys.path:
        sys.path.insert(0, VENDOR)


def _installed(pkg: str) -> bool:
    _ensure_path()
    return importlib.util.find_spec(pkg) is not None


def _pip(*args: str) -> None:
    # --no-deps evita instalar dependencias transitivas que ya están en el entorno;
    # --target dirige los archivos a vendor/ en lugar de al site-packages del sistema.
    os.makedirs(VENDOR, exist_ok=True)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--no-deps", "-q", "--target", VENDOR, *args
    ])
    _ensure_path()
    importlib.invalidate_caches()


def ensure_deps() -> None:
    # Verifica e instala solo los paquetes que faltan; si ya están presentes no hace nada.
    _ensure_path()
    if not _installed("fairseq"):
        print("[install] Instalando fairseq...", flush=True)
        _pip("fairseq==0.12.2")
    if not _installed("rvc_python"):
        print("[install] Instalando rvc-python...", flush=True)
        _pip("rvc-python==0.1.5")
