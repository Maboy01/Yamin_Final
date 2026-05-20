import os
import tempfile
import torch
import dataclasses
import streamlit as st

# Patch 1: torch.load — PyTorch 2.6+ defaults weights_only=True, breaks fairseq HuBERT loader.
_orig_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)
torch.load = _patched_load

# Patch 2: fairseq uses mutable dataclass instances as field defaults (Python 3.10+ rejects).
# Intercept _process_class: fix only the classes that actually trigger the error.
_orig_process = dataclasses._process_class
def _lenient_process(cls, *args, **kwargs):
    try:
        return _orig_process(cls, *args, **kwargs)
    except (TypeError, ValueError) as e:
        if "mutable default" not in str(e):
            raise
        for fname in list(getattr(cls, "__annotations__", {})):
            val = cls.__dict__.get(fname, dataclasses.MISSING)
            if (val is not dataclasses.MISSING
                    and not isinstance(val, dataclasses.Field)
                    and dataclasses.is_dataclass(val)):
                setattr(cls, fname, dataclasses.field(default_factory=type(val)))
        return _orig_process(cls, *args, **kwargs)
dataclasses._process_class = _lenient_process

# Patch 3: fairseq passes dataclasses.MISSING to OmegaConf; OmegaConf rejects it
# with "Object of unsupported type: '_MISSING_TYPE'". Intercept at _node_wrap
# (the chokepoint that actually raises the error) and at _maybe_wrap (the higher-
# level wrapper). Both are patched wherever they live, since their module location
# has varied across OmegaConf versions.
import importlib
try:
    from omegaconf import MISSING as _OC_MISSING
    _MISSING_TYPE = type(dataclasses.MISSING)

    def _scrub(v):
        return _OC_MISSING if isinstance(v, _MISSING_TYPE) else v

    def _wrap(orig):
        def patched(*args, **kwargs):
            args = tuple(_scrub(a) for a in args)
            kwargs = {k: _scrub(v) for k, v in kwargs.items()}
            return orig(*args, **kwargs)
        patched._yamin_patched = True
        return patched

    _targets = [
        ("omegaconf._utils", "_node_wrap"),
        ("omegaconf.omegaconf", "_maybe_wrap"),
        ("omegaconf._utils", "_maybe_wrap"),
    ]
    _patched_any = False
    for _mod_name, _fn_name in _targets:
        try:
            _mod = importlib.import_module(_mod_name)
            _fn = getattr(_mod, _fn_name, None)
            if _fn is not None and not getattr(_fn, "_yamin_patched", False):
                setattr(_mod, _fn_name, _wrap(_fn))
                _patched_any = True
        except Exception:
            pass
    if not _patched_any:
        print("[voice_converter] WARNING: OmegaConf MISSING patch did not install",
              flush=True)
except Exception as _e:
    print(f"[voice_converter] WARNING: OmegaConf patch failed: {_e}", flush=True)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "Yamin23_50e_1300s.pth")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "Yamin23.index")


@st.cache_resource(show_spinner="Cargando modelo RVC...")
def load_rvc():
    from rvc_python.infer import RVCInference
    rvc = RVCInference(device="cpu")
    rvc.load_model(MODEL_PATH, index_path=INDEX_PATH)
    return rvc


def convert(audio_bytes: bytes, f0_up_key: int = 0, index_rate: float = 0.75) -> bytes:
    rvc = load_rvc()

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
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

    return result
