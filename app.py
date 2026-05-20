from install import ensure_deps
ensure_deps()

import io
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
st.markdown(
    '<p class="subtitle">Convierte tu voz al estilo de Goku con IA</p>',
    unsafe_allow_html=True,
)

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


# ── Main ─────────────────────────────────────────────────────────────────────
if "recorder_id" not in st.session_state:
    st.session_state["recorder_id"] = 0

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="step-label">PASO 1 — ELIGE TU AUDIO</p>', unsafe_allow_html=True)

tab_record, tab_upload, tab_text = st.tabs(["🎤 Grabar", "📁 Subir archivo", "✍️ Texto"])

audio_input = None
audio_filename = "input.wav"

with tab_record:
    recorded = st.audio_input(
        "Mantén presionado el botón para grabar",
        key=f"recorder_{st.session_state['recorder_id']}",
    )
    if recorded is not None:
        audio_input = recorded

with tab_upload:
    uploaded = st.file_uploader(
        "Arrastra o selecciona un archivo de audio",
        type=["wav", "mp3", "ogg", "flac", "m4a"],
        help="Soporta WAV, MP3, OGG, FLAC, M4A",
    )
    if uploaded is not None:
        audio_input = uploaded
        audio_filename = uploaded.name
        st.audio(uploaded)

with tab_text:
    tts_text = st.text_area(
        "Escribe lo que quieres que diga",
        placeholder="¡Voy a superar mis propios límites!",
        max_chars=400,
        label_visibility="collapsed",
    )
    if st.button("🎙️ GENERAR AUDIO", disabled=not bool(tts_text and tts_text.strip())):
        with st.spinner("Generando voz..."):
            try:
                tts_bytes = voice_converter.text_to_audio(tts_text.strip())
                st.session_state["tts_audio"] = tts_bytes
            except Exception as e:
                st.error(f"Error al generar voz: {e}")

    if "tts_audio" in st.session_state:
        st.audio(st.session_state["tts_audio"], format="audio/mpeg")
        audio_input = io.BytesIO(st.session_state["tts_audio"])
        audio_filename = "tts.mp3"

if audio_input is not None or "converted" in st.session_state:
    if st.button("🔄 REINICIAR"):
        st.session_state["recorder_id"] += 1
        for key in ("converted", "original_audio", "tts_audio"):
            st.session_state.pop(key, None)
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

if audio_input is not None and audio_filename == "input.wav":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="step-label">PASO 2 — AUDIO ORIGINAL</p>', unsafe_allow_html=True)
    st.audio(audio_input)
    st.markdown("</div>", unsafe_allow_html=True)

if audio_input is not None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="step-label">PASO 3 — CONVERTIR VOZ</p>', unsafe_allow_html=True)

    if st.button("🔥 CONVERTIR VOZ"):
        with st.spinner("Convirtiendo... (puede tardar unos segundos)"):
            try:
                raw_bytes = audio_input.read()
                st.session_state["original_audio"] = (raw_bytes, audio_filename)
                converted_bytes = voice_converter.convert(
                    audio_bytes=raw_bytes,
                    f0_up_key=f0_up_key,
                    index_rate=index_rate,
                    filename=audio_filename,
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
    st.markdown('<p class="step-label">PASO 4 — COMPARATIVA</p>', unsafe_allow_html=True)

    col_orig, col_conv = st.columns(2)
    with col_orig:
        st.markdown("**Tu voz / TTS**")
        if "original_audio" in st.session_state:
            orig_bytes, orig_fname = st.session_state["original_audio"]
            orig_fmt = "audio/mpeg" if orig_fname.endswith(".mp3") else "audio/wav"
            st.audio(orig_bytes, format=orig_fmt)
    with col_conv:
        st.markdown("**Voz de Goku 🔥**")
        st.audio(st.session_state["converted"], format="audio/wav")

    st.download_button(
        label="⬇️ DESCARGAR AUDIO CONVERTIDO",
        data=st.session_state["converted"],
        file_name="goku_voice.wav",
        mime="audio/wav",
    )
    st.markdown("</div>", unsafe_allow_html=True)
