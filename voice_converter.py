import os
import tempfile
import torch
import dataclasses
import streamlit as st

# ── Parches de compatibilidad ────────────────────────────────────────────────
# fairseq fue diseñado para versiones antiguas de Python/PyTorch/OmegaConf.
# Los tres bloques siguientes lo adaptan sin modificar su código fuente.

# Parche 1: PyTorch 2.6+ cambió el valor por defecto de weights_only a True,
# lo que hace que torch.load() rechace los checkpoints de HuBERT de fairseq.
# Forzar weights_only=False restaura el comportamiento anterior.
_orig_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)
torch.load = _patched_load

# Parche 2: Python 3.11+ prohíbe usar instancias mutables de dataclasses como
# valores por defecto de campos (lanza "mutable default ... use default_factory").
# Este parche intercepta la construcción de cada dataclass y convierte esos
# valores en lambdas (default_factory) antes de que el decorador @dataclass los rechace.
_orig_process = dataclasses._process_class
def _lenient_process(cls, *args, **kwargs):
    for fname in list(getattr(cls, "__annotations__", {})):
        val = getattr(cls, fname, dataclasses.MISSING)
        if val is dataclasses.MISSING:
            continue
        # Extrae el valor real, tanto si está envuelto en field() como si es directo.
        default_val = val.default if isinstance(val, dataclasses.Field) else val
        if (default_val is not dataclasses.MISSING
                and not isinstance(default_val, type)
                and dataclasses.is_dataclass(default_val)):
            setattr(cls, fname, dataclasses.field(default_factory=type(default_val)))
    return _orig_process(cls, *args, **kwargs)
dataclasses._process_class = _lenient_process

# Parche 3: fairseq pasa dataclasses.MISSING directamente a OmegaConf, que lo rechaza
# con "Object of unsupported type: '_MISSING_TYPE'". Se parchean las funciones internas
# _node_wrap y _maybe_wrap en todos los submódulos de omegaconf para sustituir MISSING
# por el equivalente de OmegaConf antes de que llegue al validador de tipos.
import sys
import importlib
try:
    from omegaconf import MISSING as _OC_MISSING, OmegaConf as _OmegaConf
    _MISSING_TYPE = type(dataclasses.MISSING)

    def _scrub(v):
        return _OC_MISSING if isinstance(v, _MISSING_TYPE) else v

    def _wrap(orig):
        if getattr(orig, "_yamin_patched", False):
            return orig
        def patched(*args, **kwargs):
            args = tuple(_scrub(a) for a in args)
            kwargs = {k: _scrub(v) for k, v in kwargs.items()}
            return orig(*args, **kwargs)
        patched._yamin_patched = True
        return patched

    # Force-load the submodules likely to hold local references to the wrappers
    for _sub in ("omegaconf._utils", "omegaconf.omegaconf",
                 "omegaconf.dictconfig", "omegaconf.listconfig",
                 "omegaconf.basecontainer", "omegaconf._impl"):
        try:
            importlib.import_module(_sub)
        except Exception:
            pass

    _patch_count = 0
    for _mod_name, _mod in list(sys.modules.items()):
        if not _mod_name.startswith("omegaconf"):
            continue
        for _attr in ("_node_wrap", "_maybe_wrap"):
            _fn = getattr(_mod, _attr, None)
            if callable(_fn) and not getattr(_fn, "_yamin_patched", False):
                setattr(_mod, _attr, _wrap(_fn))
                _patch_count += 1

    # Safety net: scrub input to OmegaConf.create / OmegaConf.structured
    def _wrap_create(orig):
        def patched(*args, **kwargs):
            args = tuple(_scrub(a) for a in args)
            kwargs = {k: _scrub(v) for k, v in kwargs.items()}
            return orig(*args, **kwargs)
        patched._yamin_patched = True
        return patched
    for _meth in ("create", "structured"):
        _fn = getattr(_OmegaConf, _meth, None)
        if _fn is not None and not getattr(_fn, "_yamin_patched", False):
            setattr(_OmegaConf, _meth, _wrap_create(_fn))
            _patch_count += 1

    print(f"[voice_converter] OmegaConf MISSING patch installed "
          f"({_patch_count} hooks)", flush=True)
except Exception as _e:
    print(f"[voice_converter] WARNING: OmegaConf patch failed: {_e}", flush=True)

# Rutas a los archivos del modelo entrenado con la voz objetivo.
# El .pth contiene los pesos de la red neuronal; el .index es el índice FAISS
# de vectores de características de timbre extraídos durante el entrenamiento.
MODEL_PATH = os.path.join(os.path.dirname(__file__), "Yamin23_50e_1300s.pth")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "Yamin23.index")


@st.cache_resource(show_spinner="Cargando modelo RVC...")
def load_rvc():
    # @st.cache_resource garantiza que el modelo se cargue solo una vez por sesión
    # del servidor, evitando leer los pesos desde disco en cada conversión.
    from rvc_python.infer import RVCInference
    rvc = RVCInference(device="cpu")
    rvc.load_model(MODEL_PATH, index_path=INDEX_PATH)
    return rvc


def _ensure_wav(audio_bytes: bytes, filename: str) -> bytes:
    # RVC solo acepta WAV; si el archivo de entrada tiene otro formato se
    # decodifica con librosa (que admite MP3, OGG, FLAC, M4A, etc.) y se
    # reencoda como WAV PCM de 16 bits antes de pasarlo al modelo.
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".wav":
        return audio_bytes
    import io, librosa, soundfile as sf
    y, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def convert(audio_bytes: bytes, f0_up_key: int = 0, index_rate: float = 0.75,
            filename: str = "input.wav") -> bytes:
    rvc = load_rvc()
    audio_bytes = _ensure_wav(audio_bytes, filename)

    # RVC opera sobre archivos en disco, no sobre buffers en memoria,
    # por eso se usan archivos temporales que se borran al finalizar.
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        input_path = tmp_in.name

    output_path = input_path.replace(".wav", "_out.wav")

    try:
        rvc.set_params(f0up_key=f0_up_key, index_rate=index_rate)
        rvc.infer_file(input_path=input_path, output_path=output_path)
        with open(output_path, "rb") as f:
            result = f.read()
    finally:
        # Limpieza garantizada aunque la inferencia falle.
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

    return result


def text_to_audio(text: str, voice: str = "es-MX-JorgeNeural") -> bytes:
    # Usa Edge TTS (motor de síntesis de voz de Microsoft) para convertir texto a audio MP3.
    # La voz "es-MX-JorgeNeural" es masculina en español de México; es el punto de partida
    # antes de que RVC la transforme al timbre de Goku.
    import edge_tts
    import asyncio
    import io
    import threading

    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    result = [None]
    exc = [None]

    # Streamlit corre en su propio loop de eventos; asyncio.run() no puede anidarse
    # en él directamente, así que se lanza en un hilo separado con su propio loop.
    def _thread():
        try:
            result[0] = asyncio.run(_run())
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=_thread)
    t.start()
    t.join()
    if exc[0]:
        raise exc[0]
    return result[0]
