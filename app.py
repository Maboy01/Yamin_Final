from install import ensure_deps
ensure_deps()

import streamlit as st
import voice_converter

st.set_page_config(
    page_title="Doblaje Goku",
    page_icon="🔥",
    layout="centered",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bangers&family=Roboto:wght@400;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }

        .stApp {
            background: radial-gradient(ellipse at top, #1a0a00 0%, #0d0d1a 60%, #000000 100%);
            color: #f0e6d3;
        }

        h1.main-title {
            font-family: 'Bangers', cursive;
            font-size: 3.5rem;
            letter-spacing: 4px;
            color: #ffd700;
            text-shadow: 0 0 20px #ff6b00, 0 0 40px #ff6b00, 2px 2px 0 #8b0000;
            text-align: center;
            margin-bottom: 0;
        }

        .subtitle {
            text-align: center;
            color: #ff9a3c;
            font-size: 1rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: 0;
            margin-bottom: 2rem;
        }

        .stButton > button {
            background: linear-gradient(135deg, #ff6b00, #ff0000);
            color: white;
            font-family: 'Bangers', cursive;
            font-size: 1.3rem;
            letter-spacing: 2px;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 2rem;
            width: 100%;
            box-shadow: 0 4px 15px rgba(255, 107, 0, 0.5);
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(255, 107, 0, 0.8);
        }

        .stDownloadButton > button {
            background: linear-gradient(135deg, #1a5c2e, #0d3b1e);
            color: #7fff7f;
            font-family: 'Bangers', cursive;
            font-size: 1.1rem;
            letter-spacing: 2px;
            border: 1px solid #3aff3a;
            border-radius: 8px;
            width: 100%;
        }

        .stSlider label { color: #ff9a3c; font-weight: 700; }

        .section-card {
            background: rgba(255, 107, 0, 0.05);
            border: 1px solid rgba(255, 107, 0, 0.2);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        .step-label {
            font-family: 'Bangers', cursive;
            font-size: 1.1rem;
            color: #ff6b00;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }

        footer { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<h1 class="main-title">⚡ DOBLAJE GOKU ⚡</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Powered by RVC — Applio Model</p>', unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    st.markdown("---")

    f0_up_key = st.slider(
        "🎵 Tono (Pitch)",
        min_value=-12,
        max_value=12,
        value=0,
        step=1,
        help="Sube o baja el tono en semitonos. 0 = sin cambio.",
    )

    index_rate = st.slider(
        "🧬 Index Rate",
        min_value=0.0,
        max_value=1.0,
        value=0.75,
        step=0.05,
        help="Qué tanto influye el índice FAISS. Más alto = más parecido al modelo.",
    )

    st.markdown("---")
    st.markdown("**Modelo cargado:**")
    st.code("Yamin23_50e_1300s.pth", language=None)
    st.markdown("**Índice:**")
    st.code("Yamin23.index", language=None)

# ── Main ─────────────────────────────────────────────────────────────────────
if "recorder_id" not in st.session_state:
    st.session_state["recorder_id"] = 0

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="step-label">PASO 1 — GRABA TU VOZ</p>', unsafe_allow_html=True)
audio_input = st.audio_input(
    "Mantén presionado el botón para grabar",
    key=f"recorder_{st.session_state['recorder_id']}",
)

if audio_input is not None or "converted" in st.session_state:
    if st.button("🔄 REINICIAR (grabar otro audio)"):
        st.session_state["recorder_id"] += 1
        st.session_state.pop("converted", None)
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

if audio_input is not None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="step-label">PASO 2 — AUDIO ORIGINAL</p>', unsafe_allow_html=True)
    st.audio(audio_input, format="audio/wav")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="step-label">PASO 3 — CONVERTIR VOZ</p>', unsafe_allow_html=True)

    if st.button("🔥 CONVERTIR VOZ"):
        with st.spinner("Convirtiendo... (puede tardar unos segundos)"):
            try:
                converted_bytes = voice_converter.convert(
                    audio_bytes=audio_input.read(),
                    f0_up_key=f0_up_key,
                    index_rate=index_rate,
                )
                st.session_state["converted"] = converted_bytes
                st.success("¡Conversión completada!")
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                st.error(f"Error durante la conversión: {e}")
                with st.expander("Ver traceback completo (debug)", expanded=True):
                    st.code(tb, language="python")
                print(tb, flush=True)

    st.markdown("</div>", unsafe_allow_html=True)

if "converted" in st.session_state:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="step-label">PASO 4 — RESULTADO</p>', unsafe_allow_html=True)
    st.audio(st.session_state["converted"], format="audio/wav")

    st.download_button(
        label="⬇️ DESCARGAR AUDIO CONVERTIDO",
        data=st.session_state["converted"],
        file_name="yamin_converted.wav",
        mime="audio/wav",
    )
    st.markdown("</div>", unsafe_allow_html=True)
