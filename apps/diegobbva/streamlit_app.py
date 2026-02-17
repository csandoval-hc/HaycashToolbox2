# -----------------------------
# Bootstrap for Streamlit Cloud multipage execution
# - Ensures local module imports work (codigo_diego)
# - Keeps relative-path behavior consistent if the original script expects it
# -----------------------------
import os
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent

# Make sure this app folder is importable (so "import codigo_diego" works)
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# If the original script reads/writes relative paths, keep behavior stable
try:
    os.chdir(str(_APP_DIR))
except Exception:
    pass


import streamlit as st
import tempfile

# Import original logic without changes
import codigo_diego as logic

st.set_page_config(page_title="BBVA Domiciliación (300 bytes)", layout="centered")

st.title("BBVA Domiciliación – FIXED (300 bytes)")
st.caption("Genera un TXT de 300 bytes por registro (latin-1, CRLF), usando la misma lógica del script original.")

uploaded = st.file_uploader("Excel/CSV entrada", type=["xlsx", "xls", "xlsm", "csv"])

c1, c2 = st.columns(2)
with c1:
    fecha = st.text_input("Fecha (AAAAMMDD) — vacío = hoy", value="")
with c2:
    ref_inicial = st.text_input("Ref inicial", value="1204000")

st.subheader("Parámetros (solo lectura)")
p1, p2, p3 = st.columns([1, 1, 2])
p1.text_input("Bloque", value=logic.BLOQUE_DEFAULT, disabled=True)
p2.text_input("RFC emisor", value=logic.RFC_EMISOR_DEFAULT, disabled=True)
p3.text_input("Razón social", value=logic.BUSINESS_EMISOR_STR, disabled=True)

# Keep default behavior; this field exists only if you want to override.
bloque_override = st.text_input("Bloque (opcional)", value=logic.BLOQUE_DEFAULT)

st.divider()


def _safe_int(s: str, default: int) -> int:
    try:
        return int(str(s).strip())
    except Exception:
        return default


if st.button("Generar TXT"):
    if uploaded is None:
        st.error("Selecciona el Excel/CSV de entrada.")
        st.stop()

    start_ref = _safe_int(ref_inicial, 1204000)
    bloque = (bloque_override or logic.BLOQUE_DEFAULT)

    with tempfile.TemporaryDirectory() as td:
        in_path = os.path.join(td, uploaded.name)
        with open(in_path, "wb") as f:
            f.write(uploaded.getbuffer())

        out_name = f"{Path(uploaded.name).stem}_BBVA_FIXED.txt"
        out_path = os.path.join(td, out_name)

        try:
            logic.generate_bbva_file(in_path, out_path, fecha, start_ref, bloque)
        except Exception as e:
            st.exception(e)
            st.stop()

        data = Path(out_path).read_bytes()

    st.success("Archivo generado.")
    st.download_button("Descargar TXT", data=data, file_name=out_name, mime="text/plain")
