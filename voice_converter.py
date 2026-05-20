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

# Patch 2: fairseq uses mutable dataclass instances as field defaults; Python 3.11+
# rejects with "mutable default ... use default_factory". Pre-process the class BEFORE
# @dataclass runs to convert ANY dataclass-instance default (raw or wrapped in field())
# into an equivalent default_factory. Covers inherited fields via getattr.
_orig_process = dataclasses._process_class
def _lenient_process(cls, *args, **kwargs):
    for fname in list(getattr(cls, "__annotations__", {})):
        val = getattr(cls, fname, dataclasses.MISSING)
        if val is dataclasses.MISSING:
            continue
        # Extract underlying default (handles both `x: T = T()` and `x: T = field(default=T())`)
        default_val = val.default if isinstance(val, dataclasses.Field) else val
        if (default_val is not dataclasses.MISSING
                and not isinstance(default_val, type)
                and dataclasses.is_dataclass(default_val)):
            setattr(cls, fname, dataclasses.field(default_factory=type(default_val)))
    return _orig_process(cls, *args, **kwargs)
dataclasses._process_class = _lenient_process

# Patch 3: fairseq passes dataclasses.MISSING to OmegaConf; OmegaConf rejects it
# with "Object of unsupported type: '_MISSING_TYPE'". Walk every loaded omegaconf
# submodule and rewrite any reference to _node_wrap / _maybe_wrap, since those
# functions get re-imported by name across multiple submodules (dictconfig,
# listconfig, omegaconf) and a single-module patch misses local references.
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
