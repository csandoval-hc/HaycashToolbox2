# -*- coding: utf-8 -*-
"""
Streamlit port of the original R/Shiny "Lector Contrato" app.

- Upload one or more contract PDFs
- Extract:
    * Capital (Anticipo)
    * Valor pagaré / Devolución
    * CPA (Comisión por apertura) %
    * Monto mínimo mensual (min_payment)
- Preview + status + Excel download (includes *_raw columns)

Notes:
- If a PDF has no embedded text, the app can OCR pages using Tesseract.
- Configure Tesseract by either:
    (a) installing it and making "tesseract" available in PATH, or
    (b) setting env var TESSERACT_CMD to the full path of tesseract.exe
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import pypdfium2 as pdfium
except Exception as e:
    pdfium = None  # handled later

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None


# -----------------------------
# Config / constants
# -----------------------------

MONEY_REGEX = re.compile(r"\$\s*\d{1,3}(?:[ ,]\d{3})*(?:\.\d{2})?", re.IGNORECASE)
PCT_REGEX = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%\b", re.IGNORECASE)

ANCHOR_CAPITAL = re.compile(
    r"HayCash\s+se\s+obliga\s+a\s+transferir|cantidad\s+de\s+\$|\(\s*el\s+[“\"]Anticipo[”\"]\s*\)|\bel\s+[“\"]Anticipo[”\"]\b",
    re.IGNORECASE,
)
ANCHOR_PAGARE = re.compile(
    r"se\s+obliga\s+a\s+devolver\s+a\s+HayCash|devolver\s+a\s+HayCash\s+la\s+suma\s+de|\(\s*la\s+[“\"]Devoluci[oó]n[”\"]\s*\)|\bel\s+[“\"]Devoluci[oó]n[”\"]\b",
    re.IGNORECASE,
)
ANCHOR_CPA = re.compile(r"comisi[oó]n\s+por\s+apertura|comisi[oó]n\s+de\s+apertura", re.IGNORECASE)

ANCHOR_MONTO_MINIMO_MENSUAL = re.compile(
    r"\(\s*el\s+[“\"]?Monto\s+M[ií]nimo\s+Mensual[”\"]?\s*\)", re.IGNORECASE
)


# -----------------------------
# Helpers (ported from R)
# -----------------------------

def normalize_text(pages: List[str]) -> str:
    """
    R version:
      paste(pages, collapse = "\n") %>% tolower() %>%
      str_replace_all("\r", " ") %>% str_replace_all("[[:space:]]+", " ") %>% str_squish()
    """
    text = "\n".join([p or "" for p in pages])
    text = text.replace("\r", " ")
    text = text.lower()
    # normalize whitespace
    text = re.sub(r"\s+", " ", text, flags=re.UNICODE).strip()
    return text


def money_to_num(x: Optional[str]) -> Optional[float]:
    if not x or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x)
    s = re.sub(r"[$\s]", "", s)
    s = s.replace(",", "")
    # allow "1 234" thousands
    s = s.replace(" ", "")
    try:
        return float(s)
    except Exception:
        return None


def pct_to_num(x: Optional[str]) -> Optional[float]:
    if not x or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return None


@dataclass
class Hit:
    start: int
    end: int
    value: str


def extract_all_with_pos(text: str, pattern: re.Pattern) -> List[Hit]:
    hits: List[Hit] = []
    for m in pattern.finditer(text):
        hits.append(Hit(start=m.start(), end=m.end(), value=m.group(0)))
    return hits


def _window_around_anchor(text: str, anchor_span: Tuple[int, int], window: int) -> Tuple[str, int]:
    """
    Returns (chunk, start_offset_in_original)
    """
    a_start, a_end = anchor_span
    start = max(0, a_start - window)
    end = min(len(text), a_end + window)
    return text[start:end], start


def extract_money_near(text: str, anchor_regex: re.Pattern, window: int = 1200, prefer: str = "nearest") -> Tuple[Optional[str], Optional[str]]:
    a = anchor_regex.search(text)
    if not a:
        return None, None

    chunk, chunk_start = _window_around_anchor(text, (a.start(), a.end()), window)
    hits = extract_all_with_pos(chunk, MONEY_REGEX)
    if not hits:
        return None, chunk

    if prefer == "first":
        pick = hits[0].value
    elif prefer == "last":
        pick = hits[-1].value
    else:
        anchor_center = (a.start() + a.end()) / 2
        anchor_center_in_chunk = anchor_center - chunk_start
        best = min(hits, key=lambda h: abs(((h.start + h.end) / 2) - anchor_center_in_chunk))
        pick = best.value

    return pick.strip(), chunk


def extract_pct_near(text: str, anchor_regex: re.Pattern, window: int = 900, prefer: str = "nearest") -> Tuple[Optional[str], Optional[str]]:
    a = anchor_regex.search(text)
    if not a:
        return None, None

    chunk, chunk_start = _window_around_anchor(text, (a.start(), a.end()), window)
    hits = extract_all_with_pos(chunk, PCT_REGEX)
    if not hits:
        return None, chunk

    if prefer == "first":
        pick = hits[0].value
    elif prefer == "last":
        pick = hits[-1].value
    else:
        anchor_center = (a.start() + a.end()) / 2
        anchor_center_in_chunk = anchor_center - chunk_start
        best = min(hits, key=lambda h: abs(((h.start + h.end) / 2) - anchor_center_in_chunk))
        pick = best.value

    return pick.strip(), chunk


def extract_money_just_before_monto_minimo_mensual(text: str, window: int = 2400) -> Tuple[Optional[str], Optional[str]]:
    a = ANCHOR_MONTO_MINIMO_MENSUAL.search(text)
    if not a:
        return None, None

    end = a.start()
    start = max(0, end - window)
    chunk = text[start:end]

    hits = extract_all_with_pos(chunk, MONEY_REGEX)
    if not hits:
        return None, chunk

    return hits[-1].value.strip(), chunk


# -----------------------------
# PDF reading (text + OCR fallback)
# -----------------------------

def _configure_tesseract_from_env() -> None:
    """
    If user sets $env:TESSERACT_CMD in PowerShell, we pick it up.
    """
    if pytesseract is None:
        return
    cmd = os.getenv("TESSERACT_CMD") or os.getenv("TESSERACT_PATH")
    if cmd and os.path.exists(cmd):
        pytesseract.pytesseract.tesseract_cmd = cmd


def pdf_text_pages(pdf_path: str, ocr_if_empty: bool = True, ocr_lang: str = "spa") -> List[str]:
    """
    Extract embedded text per page via PDFium.
    If text is mostly empty and OCR is available, OCR each page image.
    """
    if pdfium is None:
        raise RuntimeError("pypdfium2 is not installed or failed to import.")

    _configure_tesseract_from_env()

    doc = pdfium.PdfDocument(pdf_path)
    pages_text: List[str] = []

    for i in range(len(doc)):
        page = doc[i]
        try:
            textpage = page.get_textpage()
            txt = textpage.get_text_range()
        except Exception:
            txt = ""
        pages_text.append(txt or "")

    joined = normalize_text(pages_text)
    if not ocr_if_empty:
        return pages_text

    # If embedded text is very small, try OCR (requires pytesseract + PIL + installed tesseract)
    if len(joined) < 200:
        if pytesseract is None or Image is None:
            return pages_text

        ocr_pages: List[str] = []
        for i in range(len(doc)):
            page = doc[i]
            try:
                # render at higher scale for OCR
                pil_image = page.render(scale=2).to_pil()
                ocr_txt = pytesseract.image_to_string(pil_image, lang=ocr_lang)
            except Exception:
                ocr_txt = ""
            ocr_pages.append(ocr_txt or "")
        return ocr_pages

    return pages_text


# -----------------------------
# Main extractor
# -----------------------------

def extract_fields_from_pdf(pdf_path: str) -> dict:
    pages = pdf_text_pages(pdf_path, ocr_if_empty=True, ocr_lang="spa")
    text = normalize_text(pages)

    cap_raw, _ = extract_money_near(text, ANCHOR_CAPITAL, window=1200, prefer="nearest")
    pag_raw, _ = extract_money_near(text, ANCHOR_PAGARE, window=1400, prefer="nearest")
    cpa_raw, _ = extract_pct_near(text, ANCHOR_CPA, window=900, prefer="nearest")
    mp_raw, _ = extract_money_just_before_monto_minimo_mensual(text, window=2400)

    return {
        "file_name": Path(pdf_path).name,
        "file_path": str(Path(pdf_path).resolve()),
        "capital_raw": cap_raw,
        "capital": money_to_num(cap_raw),
        "valor_pagare_raw": pag_raw,
        "valor_pagare": money_to_num(pag_raw),
        "cpa_raw": cpa_raw,
        "cpa": pct_to_num(cpa_raw),
        "min_payment_raw": mp_raw,
        "min_payment": money_to_num(mp_raw),
    }


def build_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    Writes an XLSX in-memory. Requires openpyxl.
    """
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="extraccion")
    return out.getvalue()


# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="Lector de Contratos (PDF) → Excel", layout="wide")

st.title("Extracción de datos desde contratos (PDF) → Excel")

with st.sidebar:
    st.subheader("Entrada")
    uploaded = st.file_uploader("Sube uno o varios PDFs", type=["pdf"], accept_multiple_files=True)

    st.subheader("OCR (opcional)")
    st.caption("Solo se usa si el PDF no tiene texto embebido.")
    tcmd = st.text_input("Ruta a tesseract.exe (opcional)", value=os.getenv("TESSERACT_CMD", ""))
    if tcmd:
        os.environ["TESSERACT_CMD"] = tcmd

    run = st.button("Procesar PDFs", use_container_width=True)

    st.divider()
    st.subheader("Salida")
    st.caption("Tip: si un contrato queda en NA, revisa *_raw en el Excel para ver qué capturó.")

# Keep same behavior as Shiny: only process on button click
if "results_df" not in st.session_state:
    st.session_state["results_df"] = None
if "status" not in st.session_state:
    st.session_state["status"] = "Carga PDFs y presiona 'Procesar PDFs'."

if run:
    if not uploaded:
        st.session_state["results_df"] = None
        st.session_state["status"] = "No se subieron PDFs."
    else:
        rows = []
        errors = 0
        # Save uploads to a temp folder so pdfium can open them
        tmp_dir = Path(st.session_state.get("tmp_dir", str(Path.cwd() / "_tmp_uploads")))
        tmp_dir.mkdir(parents=True, exist_ok=True)
        st.session_state["tmp_dir"] = str(tmp_dir)

        for uf in uploaded:
            try:
                tmp_path = tmp_dir / uf.name
                tmp_path.write_bytes(uf.getbuffer())
                rows.append(extract_fields_from_pdf(str(tmp_path)))
            except Exception:
                errors += 1
                rows.append({
                    "file_name": uf.name,
                    "file_path": "",
                    "capital_raw": None,
                    "capital": None,
                    "valor_pagare_raw": None,
                    "valor_pagare": None,
                    "cpa_raw": None,
                    "cpa": None,
                    "min_payment_raw": None,
                    "min_payment": None,
                })

        df = pd.DataFrame(rows)
        st.session_state["results_df"] = df

        st.session_state["status"] = (
            f"Procesados: {len(df)} PDF(s)\n"
            f"Errores: {errors}\n"
            f"Sin Capital: {df['capital'].isna().sum()}\n"
            f"Sin Valor pagaré: {df['valor_pagare'].isna().sum()}\n"
            f"Sin CPA: {df['cpa'].isna().sum()}\n"
            f"Sin min_payment: {df['min_payment'].isna().sum()}\n"
        )

df = st.session_state.get("results_df")

col1, col2 = st.columns([3, 2], gap="large")

with col1:
    st.subheader("Vista previa")
    if df is None or df.empty:
        st.info("Sin resultados todavía.")
    else:
        preview = df[["file_name", "capital", "valor_pagare", "cpa", "min_payment"]].copy()
        st.dataframe(preview, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Estado")
    st.code(st.session_state.get("status", ""), language="text")

    if df is not None and not df.empty:
        try:
            xlsx_bytes = build_excel_bytes(df)
            st.download_button(
                "Descargar Excel",
                data=xlsx_bytes,
                file_name=f"extraccion_contratos_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error("No se pudo generar el Excel. Instala openpyxl: pip install openpyxl")
