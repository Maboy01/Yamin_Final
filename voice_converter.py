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
    except TypeError as e:
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

# Patch 3: OmegaConf 2.3.0 doesn't recognize dataclasses.MISSING (only omegaconf.MISSING).
# fairseq 0.12.2 passes dataclasses.MISSING into OmegaConf internals → TypeError.
try:
    from omegaconf import _utils as _oc_utils, MISSING as _OC_MISSING
    _orig_mw = _oc_utils._maybe_wrap
    def _patched_mw(ref_type, key, value, *args, **kwargs):
        if type(value).__name__ == "_MISSING_TYPE":
            value = _OC_MISSING
        return _orig_mw(ref_type, key, value, *args, **kwargs)
    _oc_utils._maybe_wrap = _patched_mw
except Exception:
    pass

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
