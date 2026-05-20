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

# Patch 2: fairseq uses mutable dataclass instances as field defaults, which Python 3.10+
# rejects. Replace any such field with field(default_factory=type(val)) before @dataclass runs.
_orig_dc = dataclasses.dataclass
def _permissive_dc(cls=None, /, **kwargs):
    def apply(klass):
        for fname in list(getattr(klass, "__annotations__", {})):
            val = klass.__dict__.get(fname, dataclasses.MISSING)
            if (val is not dataclasses.MISSING
                    and not isinstance(val, dataclasses.Field)
                    and dataclasses.is_dataclass(val)):
                _t = type(val)
                setattr(klass, fname, dataclasses.field(default_factory=_t))
        return _orig_dc(klass, **kwargs)
    return apply if cls is None else apply(cls)
dataclasses.dataclass = _permissive_dc

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
