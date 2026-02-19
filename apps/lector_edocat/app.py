# -*- coding: utf-8 -*-
"""
Streamlit port of lectura_edocta.R (Shiny) - "Análisis de Estado de Cuenta (OCR)"

Key points:
- Renders each PDF page to an image using pypdfium2 (no Poppler needed)
- Runs OCR with Tesseract (Spanish by default: "spa")
- Extracts summary values via regex patterns (same as original R)
"""

from __future__ import annotations

import os
import re
import io
from typing import Optional, Dict

import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract

# PDF rendering (no poppler dependency)
import pypdfium2 as pdfium


# -----------------------------
# Config
# -----------------------------
MAX_UPLOAD_MB = 30
DEFAULT_LANG = "spa"

# Optional: allow overriding where tesseract.exe is (Windows)
# Set env var TESSERACT_CMD to the full path of tesseract.exe if it's not on PATH.
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]

# Optional: allow overriding tessdata directory (where spa.traineddata exists)
# In Windows, you can set TESSDATA_PREFIX to "...\\tessdata"
# Example: setx TESSDATA_PREFIX "C:\Program Files\Tesseract-OCR\tessdata"
if os.getenv("TESSDATA_PREFIX"):
    os.environ["TESSDATA_PREFIX"] = os.environ["TESSDATA_PREFIX"]


# -----------------------------
# Styling (match original look)
# -----------------------------
COLORES = {
    "fondo": "#FEFCE8",
    "texto": "#1F2937",
    "borde": "#FBBF24",
    "tarjeta": "#FFFFFF",
    "sombra": "rgba(0,0,0,0.05)",
    "boton": "#FACC15",
    "boton_hover": "#FBBF24",
}

CSS = f"""
<style>
/* Page background + base font */
.stApp {{
  background-color: {COLORES["fondo"]};
  color: {COLORES["texto"]};
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}

/* Header */
.hc-header {{
  background-color: {COLORES["tarjeta"]};
  border-bottom: 5px solid {COLORES["borde"]};
  text-align: center;
  padding: 30px 0 20px 0;
  margin-bottom: 30px;
  box-shadow: 0 2px 8px {COLORES["sombra"]};
  border-radius: 0px;
}}
.hc-header h1 {{
  font-size: 28px;
  font-weight: 800;
  margin: 0;
}}

/* Cards */
.hc-card {{
  background-color: {COLORES["tarjeta"]};
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px {COLORES["sombra"]};
}}

</style>
"""


# -----------------------------
# Helpers
# -----------------------------
CURRENCY_RE = re.compile(r"[0-9][0-9,]*\.?[0-9]*")

def _parse_money_from_match(s: str) -> Optional[float]:
    """
    Extract numeric value from something like '$ 12,345.67' -> 12345.67
    """
    if not s:
        return None
    m = CURRENCY_RE.search(s.replace(" ", ""))
    if not m:
        return None
    num = m.group(0).replace(",", "")
    try:
        return float(num)
    except ValueError:
        return None

def extract_value(pattern: str, text: str) -> Optional[float]:
    """
    R equivalent:
      m <- regexpr(patron, texto, perl=TRUE); match <- regmatches(...)
      as.numeric(gsub("[^0-9.]", "", match))
    Python:
      search regex and then pull the first currency-like number.
    """
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return _parse_money_from_match(m.group(0))

def money_fmt(x: Optional[float]) -> str:
    if x is None:
        return ""
    # mimic scales::dollar(prefix="$ ", big.mark=",")
    return f"$ {x:,.2f}"

def render_pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> list[Image.Image]:
    """
    Render PDF pages to PIL Images using pypdfium2 (no poppler).
    """
    pdf = pdfium.PdfDocument(pdf_bytes)
    images: list[Image.Image] = []
    for i in range(len(pdf)):
        page = pdf[i]
        # scale ~ dpi/72
        scale = dpi / 72.0
        pil_image = page.render(scale=scale).to_pil()
        images.append(pil_image)
    return images

def ocr_images(images: list[Image.Image], lang: str = DEFAULT_LANG) -> str:
    """
    OCR each image and concatenate with the same separator used in the R script.
    """
    parts: list[str] = []
    for img in images:
        parts.append(pytesseract.image_to_string(img, lang=lang))
    return "\n\n--- Página siguiente ---\n\n".join(parts)

def build_summary(text: str) -> pd.DataFrame:
    """
    Use same patterns as the R script.
    """
    patterns = {
        "Saldo_Inicial": r"Saldo Inicial.*?\$ ?[0-9,.]+",
        "Depositos": r"Dep[oó]sitos.*?\$ ?[0-9,.]+",
        "Retiros": r"Retiros.*?\$ ?[0-9,.]+",
        "Saldo_Final": r"Saldo Final.*?\$ ?[0-9,.]+",
        "Saldo_Promedio": r"Saldo Promedio.*?\$ ?[0-9,.]+",
        "Interes_Mensual": r"Inter[eé]s Nominal en el Mes.*?\$ ?[0-9,.]+",
        "ISR_Mensual": r"ISR Retenido en el Mes.*?\$ ?[0-9,.]+",
    }

    row: Dict[str, Optional[float]] = {k: extract_value(v, text) for k, v in patterns.items()}
    df = pd.DataFrame([row])

    # Format like the R code (it formatted only some columns; we format all numeric for clarity)
    for col in df.columns:
        df[col] = df[col].apply(money_fmt)

    return df


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="Análisis de Estado de Cuenta (OCR)", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

st.markdown('<div class="hc-header"><h1>Análisis de Estado de Cuenta (OCR)</h1></div>', unsafe_allow_html=True)

# Upload size limit note (Streamlit doesn't hard-enforce like Shiny; this is guidance)
left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown('<div class="hc-card">', unsafe_allow_html=True)
    st.subheader("Paso 1: Subir PDF")

    uploaded = st.file_uploader("Selecciona tu archivo PDF", type=["pdf"], accept_multiple_files=False)
    lang = st.text_input("Idioma OCR (Tesseract)", value=DEFAULT_LANG, help="Ej: spa, eng. Requiere el traineddata correspondiente.")
    dpi = st.number_input("DPI para renderizar el PDF", min_value=150, max_value=600, value=300, step=50)

    run = st.button("Procesar con OCR", type="primary")

    status_placeholder = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="hc-card">', unsafe_allow_html=True)
    st.subheader("Resumen financiero extraído")
    table_placeholder = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)

if "processing" not in st.session_state:
    st.session_state.processing = False
if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = ""

if st.session_state.processing:
    status_placeholder.info('⏳ Procesando estado de cuenta...')
elif uploaded is None:
    status_placeholder.info('Esperando archivo PDF...')
else:
    status_placeholder.info('Archivo listo. Presiona "Procesar con OCR".')

if run:
    if uploaded is None:
        st.warning("Primero sube un archivo PDF.")
    else:
        st.session_state.processing = True
        status_placeholder.info('⏳ Procesando estado de cuenta...')

        pdf_bytes = uploaded.read()

        try:
            images = render_pdf_to_images(pdf_bytes, dpi=int(dpi))
        except Exception as e:
            st.session_state.processing = False
            st.error(
                "No pude renderizar el PDF. "
                "Si estás usando otra librería de render, podrías necesitar Poppler. "
                f"Error: {e}"
            )
            st.stop()

        prog = st.progress(0)
        texts = []
        total = len(images) if images else 1

        for idx, img in enumerate(images, start=1):
            prog.progress(int((idx - 1) / total * 100))
            try:
                texts.append(pytesseract.image_to_string(img, lang=lang))
            except Exception as e:
                st.session_state.processing = False
                st.error(
                    "Falló el OCR (Tesseract). Verifica instalación y que el idioma exista (spa.traineddata). "
                    f"Error: {e}"
                )
                st.stop()

        prog.progress(100)

        st.session_state.ocr_text = "\n\n--- Página siguiente ---\n\n".join(texts)
        st.session_state.processing = False

# Show table if we have text
if st.session_state.ocr_text:
    df = build_summary(st.session_state.ocr_text)
    table_placeholder.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Ver texto OCR completo"):
        st.text(st.session_state.ocr_text)
