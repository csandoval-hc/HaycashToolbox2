# CDF_isaac.py
# Streamlit translation of the provided Shiny app (logic preserved).
# Run: streamlit run CDF_isaac.py

import os
import re
import io
import json
import math
import tempfile
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import requests

# PDF text + OCR
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

# String distance (Jaro-Winkler)
import jellyfish

# =============================================================================
# Global config (matches R)
# =============================================================================

# Equivalent to options(shiny.maxRequestSize = 1024 * 1024^2)
# Streamlit upload size is configured via server settings; not enforced here.

DIAG_MAX = 1200

TARGET_COLS = [
    "Nombres","last_name","second_last_name","birthday_at","RFC","curp","nationality",
    "industry","industry_SAT",
    "codigo_postal","province","municipality","neighborhood",
    "nombre_vialidad","numero_exterior","numero_interior",
    "clave_pais","contact_phone","contact_email","created_at"
]

def empty_row_vec() -> Dict[str, Optional[str]]:
    return {k: None for k in TARGET_COLS}

def coalesce(a, b):
    return a if a is not None else b

def safe_nzchar(x: Any) -> bool:
    if x is None:
        return False
    if isinstance(x, (list, tuple, np.ndarray, pd.Series)):
        if len(x) == 0:
            return False
        x = x[0]
    if pd.isna(x):
        return False
    s = str(x)
    return len(s) > 0

def s_trim(x: str) -> str:
    if x is None:
        return x
    return re.sub(r"\s{2,}", " ", str(x), flags=re.MULTILINE).strip()

# --- Normalización de texto para comparación ---

def _sanitize_df_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """openpyxl cannot write pandas.NA; convert missing values to None."""
    if df is None:
        return df
    df2 = df.copy()
    df2 = df2.where(pd.notna(df2), None)
    return df2

def normalize_txt(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).upper()
    # Remove accents: best-effort transliteration without adding new deps
    # Replace common accented chars used in Spanish
    s = s.translate(str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN"))
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# =============================================================================
# OpenAI config (matches R)
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_OPENAI = bool(OPENAI_API_KEY)

# Cache for industry_SAT (like R env)
INDUSTRY_SAT_CACHE: Dict[str, Optional[str]] = {}

def get_openai_embeddings(texts: List[str], model: str = "text-embedding-3-small") -> Optional[np.ndarray]:
    if not USE_OPENAI:
        return None
    if texts is None:
        return None
    if isinstance(texts, str):
        texts = [texts]
    texts = [str(t) for t in texts]
    if len(texts) == 0:
        return None

    url = "https://api.openai.com/v1/embeddings"
    body = {"model": model, "input": texts}
    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body),
        timeout=60,
    )
    if res.status_code != 200:
        # Mirror R warning behavior
        return None

    cont = res.json()
    emb_list = [item["embedding"] for item in cont.get("data", [])]
    if not emb_list:
        return None
    return np.array(emb_list, dtype=np.float32)

def cosine_sim(A: Optional[np.ndarray], b: Optional[np.ndarray]) -> Optional[np.ndarray]:
    # A: n x d, b: d
    if A is None or b is None:
        return None
    b = np.asarray(b, dtype=np.float32).reshape(-1)
    b_norm = float(np.linalg.norm(b))
    if (not np.isfinite(b_norm)) or b_norm == 0.0:
        return np.array([np.nan] * A.shape[0], dtype=np.float32)
    A_norms = np.linalg.norm(A, axis=1)
    denom = (A_norms * b_norm) + 1e-9
    return (A @ b) / denom

def openai_choose_best_sat(industry: str, candidatos: List[str]) -> Optional[int]:
    if not USE_OPENAI:
        return None
    if not safe_nzchar(industry):
        return None
    if candidatos is None or len(candidatos) == 0:
        return None

    candidatos = [str(c) for c in candidatos]
    n_opts = len(candidatos)
    opciones_txt = "\n".join([f"{i+1}) {candidatos[i]}" for i in range(n_opts)])

    user_content = (
        "Descripción libre de la actividad del contribuyente:\n"
        f"{industry}\n\n"
        "Opciones de actividades económicas SAT:\n"
        f"{opciones_txt}\n\n"
        "Instrucciones:\n"
        "- Elige la opción que sea CONCEPTUALMENTE más parecida a la descripción del contribuyente.\n"
        "- Considera el tipo de actividad (servicios, comercio, manufactura, etc.), el tipo de cliente y el contexto.\n"
        "- Si ninguna opción describe razonablemente la actividad, elige 0.\n\n"
        f"Responde ÚNICAMENTE con un número entero entre 0 y {n_opts} (0 si ninguna coincide). "
        "No expliques nada, solo el número."
    )

    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "Eres un asistente experto en actividades económicas del SAT. Solo respondes con un número entero."},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }

    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body),
        timeout=60,
    )
    if res.status_code != 200:
        return None

    cont = res.json()
    msg = (((cont.get("choices") or [{}])[0]).get("message") or {}).get("content")
    if msg is None:
        return None

    # first integer in text (R strips non-digits; keep behavior similar)
    m = re.search(r"-?\d+", str(msg))
    if not m:
        return None
    idx = int(m.group(0))
    if idx < 0:
        idx = 0
    if idx > n_opts:
        idx = n_opts
    return idx

# =============================================================================
# SAT catalogs (PF/PM) + tokens + embeddings precalc
# =============================================================================

def extract_tokens(x: str) -> List[str]:
    if x is None:
        return []
    s = str(x)
    if not s:
        return []
    toks = re.split(r"\s+", s)
    toks = [t for t in toks if len(t) >= 4]
    # unique, preserve order
    seen = set()
    out = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

@st.cache_resource(show_spinner=False)
def load_sat_catalogs() -> Dict[str, Any]:
    # Read PF
    try:
        actividades_pf = pd.read_csv("lista_PF.csv", encoding="utf-8", dtype=str, keep_default_na=False)
    except Exception:
        actividades_pf = pd.DataFrame({"valor": []})
    if "valor" not in actividades_pf.columns:
        if actividades_pf.shape[1] >= 1:
            actividades_pf["valor"] = actividades_pf.iloc[:, 0].astype(str)
        else:
            actividades_pf["valor"] = []
    else:
        actividades_pf["valor"] = actividades_pf["valor"].astype(str)

    actividades_pf["desc_base"] = actividades_pf["valor"].str.replace(r"\|\|.*$", "", regex=True)
    actividades_pf["desc_norm"] = actividades_pf["desc_base"].apply(normalize_txt)
    actividades_pf["tokens"] = actividades_pf["desc_norm"].apply(extract_tokens)

    # Read PM
    try:
        actividades_pm = pd.read_csv("lista_PM.csv", encoding="utf-8", dtype=str, keep_default_na=False)
    except Exception:
        actividades_pm = pd.DataFrame({"valor": []})
    if "valor" not in actividades_pm.columns:
        if actividades_pm.shape[1] >= 1:
            actividades_pm["valor"] = actividades_pm.iloc[:, 0].astype(str)
        else:
            actividades_pm["valor"] = []
    else:
        actividades_pm["valor"] = actividades_pm["valor"].astype(str)

    actividades_pm["desc_base"] = actividades_pm["valor"].str.replace(r"\|\|.*$", "", regex=True)
    actividades_pm["desc_norm"] = actividades_pm["desc_base"].apply(normalize_txt)
    actividades_pm["tokens"] = actividades_pm["desc_norm"].apply(extract_tokens)

    sat_emb_pf = None
    sat_emb_pm = None
    if USE_OPENAI and len(actividades_pf) > 0:
        try:
            tmp_pf = get_openai_embeddings(actividades_pf["desc_base"].tolist())
            if tmp_pf is not None:
                sat_emb_pf = tmp_pf
        except Exception:
            sat_emb_pf = None
    if USE_OPENAI and len(actividades_pm) > 0:
        try:
            tmp_pm = get_openai_embeddings(actividades_pm["desc_base"].tolist())
            if tmp_pm is not None:
                sat_emb_pm = tmp_pm
        except Exception:
            sat_emb_pm = None

    return {
        "pf": actividades_pf,
        "pm": actividades_pm,
        "emb_pf": sat_emb_pf,
        "emb_pm": sat_emb_pm,
    }

def jw_distance(a: str, b: str) -> float:
    # R stringdist jw returns a distance; jellyfish returns similarity.
    # jellyfish.jaro_winkler_similarity uses default scaling 0.1 (matches p=0.1)
    sim = jellyfish.jaro_winkler_similarity(a or "", b or "")
    return 1.0 - float(sim)

def match_industry_to_sat(industry: str, tipo_persona: str, catalogs: Dict[str, Any]) -> Optional[str]:
    if not safe_nzchar(industry):
        return None
    if not safe_nzchar(tipo_persona):
        return None

    tipo_persona = str(tipo_persona).lower()
    cache_key = f"{tipo_persona}||{industry}"
    if cache_key in INDUSTRY_SAT_CACHE:
        return INDUSTRY_SAT_CACHE[cache_key]

    if tipo_persona == "fisica":
        actividades_sat_local = catalogs["pf"]
        sat_emb_local = catalogs["emb_pf"]
    elif tipo_persona == "moral":
        actividades_sat_local = catalogs["pm"]
        sat_emb_local = catalogs["emb_pm"]
    else:
        return None

    if actividades_sat_local is None or len(actividades_sat_local) == 0:
        return None

    # 0) embeddings cosine over entire catalog
    if USE_OPENAI and sat_emb_local is not None:
        try:
            emb_q = get_openai_embeddings([industry])
            if emb_q is not None:
                sim = cosine_sim(sat_emb_local, emb_q[0, :])
                idx = int(np.nanargmax(sim))
                if np.isfinite(sim[idx]):
                    res = str(actividades_sat_local.iloc[idx]["valor"])
                    INDUSTRY_SAT_CACHE[cache_key] = res
                    return res
        except Exception:
            pass

    q_norm = normalize_txt(industry)
    if not q_norm:
        return None

    # 1) pre-filter lexical (JW distance) to top 40
    desc_norm = actividades_sat_local["desc_norm"].astype(str).tolist()
    d_all = np.array([jw_distance(q_norm, dn) for dn in desc_norm], dtype=np.float32)

    if np.all(~np.isfinite(d_all)):
        return None

    ord_idx = np.argsort(d_all)
    ord_idx = ord_idx[: min(40, len(ord_idx))]

    q_tokens = extract_tokens(q_norm)
    if len(q_tokens) > 0:
        overlaps = []
        for i in ord_idx:
            tok_vec = actividades_sat_local.iloc[int(i)]["tokens"]
            tok_vec = tok_vec if isinstance(tok_vec, list) else (tok_vec or [])
            overlaps.append(len(set(q_tokens).intersection(set(tok_vec))))
        overlaps = np.array(overlaps, dtype=np.int32)
        cand_idx = ord_idx[overlaps > 0]
        if len(cand_idx) == 0:
            cand_idx = ord_idx
    else:
        cand_idx = ord_idx

    if len(cand_idx) == 0:
        return None

    candidatos_valor = actividades_sat_local.iloc[cand_idx]["valor"].astype(str).tolist()
    candidatos_desc  = actividades_sat_local.iloc[cand_idx]["desc_base"].astype(str).tolist()
    candidatos_dist  = d_all[cand_idx]

    # 2) GPT choose best among candidates
    if USE_OPENAI:
        idx_rel = openai_choose_best_sat(industry, candidatos_desc)
        if idx_rel is not None and 1 <= idx_rel <= len(candidatos_valor):
            res = str(candidatos_valor[idx_rel - 1])
            INDUSTRY_SAT_CACHE[cache_key] = res
            return res
        # idx_rel == 0 or invalid -> fallback

    # 3) fallback: minimum distance
    best_pos = int(np.nanargmin(candidatos_dist))
    res = str(candidatos_valor[best_pos])
    INDUSTRY_SAT_CACHE[cache_key] = res
    return res

# =============================================================================
# Misc helpers (matches R)
# =============================================================================

def all_empty(x: Any) -> bool:
    if isinstance(x, dict):
        v = ["" if (vv is None or (isinstance(vv, float) and math.isnan(vv))) else str(vv) for vv in x.values()]
    else:
        v = [str(x)]
    v = ["" if s is None else s for s in v]
    return all(s == "" for s in v)

def row_is_empty(row: Dict[str, Optional[str]]) -> bool:
    if safe_nzchar(row.get("RFC")) or safe_nzchar(row.get("Nombres")):
        return False
    return all_empty(row)

def str_match_first(text: str, pattern: str, idx: int = 2) -> Optional[str]:
    try:
        m = re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    except Exception:
        return None
    if not m:
        return None
    try:
        return m.group(idx)
    except Exception:
        return None

# =============================================================================
# PDF extraction (text layer first, OCR only if needed) - matches R
# =============================================================================

def text_quality(s: str) -> float:
    if not (s and s.strip()):
        return float("-inf")
    letters = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", s)
    n_letters = len(letters)
    tokens = re.split(r"\s+", re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]", " ", s))
    tokens = [t for t in tokens if t]
    short_tokens = sum(1 for t in tokens if len(t) <= 2)
    score = (n_letters / max(1, len(s))) * 100.0 - (short_tokens / max(1, len(tokens))) * 30.0
    if len(s) > 500:
        score += 10.0
    return float(score)

def extract_pdf_text(pdf_path: str, use_ocr: bool = False, lang: str = "spa+eng") -> str:
    txt_pdf = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
            txt_pdf = "\n\n".join(pages)
    except Exception:
        txt_pdf = ""

    need_ocr = False
    if len(txt_pdf.strip()) < 80:
        need_ocr = True
    elif use_ocr:
        need_ocr = (text_quality(txt_pdf) < 5)

    if not need_ocr:
        return txt_pdf

    # OCR
    try:
        images = convert_from_path(pdf_path, dpi=450)
    except Exception:
        return txt_pdf

    ocr_texts = []
    config = "--psm 6"
    for img in images:
        try:
            ocr_texts.append(pytesseract.image_to_string(img, lang=lang, config=config))
        except Exception:
            ocr_texts.append("")
    txt_ocr = "\n\n".join(ocr_texts)

    return txt_ocr if (text_quality(txt_ocr) > text_quality(txt_pdf)) else txt_pdf

def clean_text(x: str) -> str:
    if not safe_nzchar(x):
        return x
    y = re.sub(r"\s{2,}", " ", x, flags=re.MULTILINE)
    y = re.sub(r"(?i)P[aá]gina\s*\[?\s*\d+\s*\]?\s*de\s*\[?\s*\d+\s*\]?", "", y)
    y = re.sub(r"(?i)Orden.*", "", y)
    return y.strip()

def infer_century(yy: str) -> Optional[int]:
    try:
        y = int(yy)
    except Exception:
        return None
    cur = int(date.today().strftime("%y"))
    return (2000 + y) if (y <= cur) else (1900 + y)

def birthday_from_rfc(rfc: Optional[str]) -> Optional[str]:
    r = re.sub(r"[^A-Za-z0-9]", "", (rfc or ""))
    if len(r) != 13:
        return None
    yy = infer_century(r[4:6])
    try:
        mm = int(r[6:8])
        dd = int(r[8:10])
    except Exception:
        return None
    if yy is None:
        return None
    return f"{yy:04d}-{mm:02d}-{dd:02d}"

def birthday_from_curp(curp: Optional[str]) -> Optional[str]:
    c = re.sub(r"[^A-Za-z0-9]", "", (curp or ""))
    if len(c) < 10:
        return None
    yy = infer_century(c[4:6])
    try:
        mm = int(c[6:8])
        dd = int(c[8:10])
    except Exception:
        return None
    if yy is None:
        return None
    return f"{yy:04d}-{mm:02d}-{dd:02d}"

def normalize_date_es(x: Optional[str]) -> Optional[str]:
    if not safe_nzchar(x):
        return None
    meses = {
        "ENERO":1,"FEBRERO":2,"MARZO":3,"ABRIL":4,"MAYO":5,"JUNIO":6,
        "JULIO":7,"AGOSTO":8,"SEPTIEMBRE":9,"OCTUBRE":10,"NOVIEMBRE":11,"DICIEMBRE":12
    }
    x2 = re.sub(r"\s+", " ", str(x)).upper()
    m = re.search(r"([0-9]{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+([0-9]{4})", x2)
    if not m:
        return x
    d = int(m.group(1))
    mes = m.group(2).translate(str.maketrans("ÁÉÍÓÚ", "AEIOU"))
    y = m.group(3)
    if mes not in meses:
        return x
    return f"{y}-{meses[mes]:02d}-{d:02d}"

def extract_email(text: str) -> Optional[str]:
    m = str_match_first(text, r"(?i)(Correo Electr[oó]nico|Email|E[- ]?mail)[:\s]*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", 2)
    if not safe_nzchar(m):
        m = str_match_first(text, r"(?i)([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", 1)
    return m

def extract_phone(text: str) -> Optional[str]:
    lada = str_match_first(text, r"(?i)Lada[:\s]*([0-9]{2,4})", 1)
    num1 = str_match_first(text, r"(?i)N[uú]mero[:\s]*([0-9\- ]{5,})", 1)
    if safe_nzchar(lada) and safe_nzchar(num1):
        return re.sub(r"\s+", "", f"+52{lada}{num1}")
    return str_match_first(text, r"(?i)(\+?52)?[\s-]*\(?[0-9]{2,3}\)?[\s-]*[0-9]{3,4}[\s-]*[0-9]{4}", 0)

def tipo_persona_from_rfc(rfc: Optional[str]) -> Optional[str]:
    r = re.sub(r"[^A-Za-z0-9]", "", (rfc or ""))
    if len(r) == 12:
        return "moral"
    if len(r) == 13:
        return "fisica"
    return None

def extract_actividades_top(text: str, logfun=None) -> Optional[str]:
    t = text or ""
    stop_markers = (
        r"Reg[ií]men(?:es)?|Obligaciones|Datos\s+del\s+domicilio|Datos\s+de\s+Ubicaci[oó]n|"
        r"Nombre\s+de\s+la\s+Entidad|Contacto|VALIDA\s+TU\s+INFORMACI[ÓO]N|"
        r"Av\.|Atenci[oó]n\s+telef[oó]nica|Correo\s+Electr[oó]nico|Tel\.?\s*Fijo"
    )
    pat = rf"(?is)Actividades?\s*Econ[oó]micas?\s*:?\s*[\r\n\s]*(.+?)(?:{stop_markers}|$)"
    m = re.search(pat, t, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    bloque = m.group(1) if m else ""
    if callable(logfun):
        logfun("    [debug] bloque actividades len:", len(bloque or ""))
    if not safe_nzchar(bloque):
        return None

    B = re.sub(r"\s{2,}", " ", bloque)
    B = re.sub(r"\s*(?:Orden\s+Actividad\s+Econ[oó]mica\s+Porcentaje.*?)(?=\d)", " ", B, flags=re.IGNORECASE | re.DOTALL)

    rx = r"(?i)(?:^|\s)(\d+)\s+([A-ZÁÉÍÓÚÑ0-9 .,/'\-\(\)]+?)\s+(\d{1,3})\s*%?\b(?:\s+\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?"
    m_all = re.findall(rx, B, flags=re.IGNORECASE)

    def clean_activity(x: str) -> str:
        x = s_trim(x)
        x = re.sub(r"\b\d{1,3}\s*%\b.*$", "", x, flags=re.IGNORECASE)
        x = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b.*$", "", x, flags=re.IGNORECASE)
        x = re.sub(r"\s{2,}", " ", x)
        return x

    if m_all and len(m_all) > 0:
        acts = [clean_activity(tup[1]) for tup in m_all]
        pct = []
        for tup in m_all:
            try:
                pct.append(int(tup[2]))
            except Exception:
                pct.append(-1)
        if any(p >= 0 for p in pct):
            return acts[int(np.argmax(np.array(pct)))]
        cand = [a for a in acts if a]
        if cand:
            return cand[0]

    m2 = re.search(r"(?im)^[\s\-•]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 .,/'\-\(\)]{5,})", B)
    cand = m2.group(1) if m2 else None
    if safe_nzchar(cand):
        return clean_activity(cand)
    return None

def cut_after_label_noise(x: Optional[str]) -> Optional[str]:
    if not safe_nzchar(x):
        return x
    stops = [
        r"N[úu]mero\s*Exterior", r"N[úu]mero\s*Interior", r"Nombre\s+de\s+la\s+Colonia",
        r"Nombre\s+de\s+la\s+Localidad", r"Nombre\s+del\s+Municipio", r"Demarcaci[oó]n\s+Territorial",
        r"Nombre\s+de\s+la\s+Entidad\s+Federativa", r"Entre\s+Calle", r"Y\s+Calle",
        r"Correo\s+Electr[oó]nico", r"Tel\.?\s*Fijo", r"Actividades?\s+Econ[oó]micas?"
    ]
    pat_stop = rf"(?is)\s*(?:{'|'.join(stops)})\b.*$"
    return s_trim(re.sub(pat_stop, "", str(x), flags=re.IGNORECASE | re.DOTALL))

def truncate_before_NOMBRE(x: Optional[str]) -> Optional[str]:
    if not safe_nzchar(x):
        return x
    return s_trim(re.sub(r"(?is)\s*NOMBRE\b.*$", "", str(x), flags=re.IGNORECASE | re.DOTALL))

# =============================================================================
# Parsers (CSF / CFDI) - matches R
# =============================================================================

def parse_csf_fields(text: str, logfun=None) -> Dict[str, Any]:
    out = empty_row_vec()


    # --- CSF PDFs often come with concatenated labels (no spaces). Normalize common labels
    # so the existing regexes (which expect spaces) can work reliably.
    label_fixes = [
        (r"NombredelaEntidadFederativa", "Nombre de la Entidad Federativa"),
        (r"NombredelMunicipiooDemarcaciónTerritorial", "Nombre del Municipio o Demarcación Territorial"),
        (r"NombredelMunicipiooDemarcacionTerritorial", "Nombre del Municipio o Demarcación Territorial"),
        (r"NombredelaColonia", "Nombre de la Colonia"),
        (r"NombredelaLocalidad", "Nombre de la Localidad"),
        (r"TipodeVialidad", "Tipo de Vialidad"),
        (r"NombredeVialidad", "Nombre de Vialidad"),
        (r"NúmeroExterior", "Número Exterior"),
        (r"NumeroExterior", "Número Exterior"),
        (r"NúmeroInterior", "Número Interior"),
        (r"NumeroInterior", "Número Interior"),
        (r"Fechainiciodeoperaciones", "Fecha inicio de operaciones"),
        (r"Fechadeúltimocambiodeestado", "Fecha de último cambio de estado"),
        (r"PrimerApellido", "Primer Apellido"),
        (r"SegundoApellido", "Segundo Apellido"),
        (r"Denominación/RazónSocial", "Denominación/Razón Social"),
        (r"Denominacion/RazonSocial", "Denominación/Razón Social"),
    ]
    for a, b in label_fixes:
        text = re.sub(a, b, text, flags=re.IGNORECASE)

    nombres_val = None
    full_rs_val = None
    full_rs_exact = None

    try:
        rfc = (
            str_match_first(text, r"(?i)R\.?F\.?C\.?[:\s]*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3})", 1)
            or str_match_first(text, r"(?i)RFC[:\s]*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3})", 1)
        )
        if safe_nzchar(rfc):
            out["RFC"] = str(rfc).upper()

        curp = str_match_first(text, r"(?i)CURP[:\s]*([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2})", 1)
        if safe_nzchar(curp):
            out["curp"] = str(curp).upper()

        nombres_val = str_match_first(
            text,
            r"(?is)Nombre\s*\(s\)[:\s]*([A-ZÁÉÍÓÚÑ0-9 .,'-]{2,}?)(?=\s*(?:Primer\s*Apellido|Segundo\s*Apellido|R\.?F\.?C\.?|RFC|CURP|$))",
            1
        )

        ap1 = str_match_first(text, r"(?i)Primer\s*Apellido[:\s]*([A-ZÁÉÍÓÚÑ .,'-]{2,})", 1)
        ap2 = str_match_first(text, r"(?i)Segundo\s*Apellido[:\s]*([A-ZÁÉÍÓÚÑ .,'-]{2,})", 1)

        full_rs_val = str_match_first(
            text,
            r"(?is)(?:Denominaci[oó]n|Raz[oó]n\s*Social|Nombre,\s*denominaci[oó]n\s*o\s*raz[oó]n\s*social)[:\s]*([A-ZÁÉÍÓÚÑ0-9 .,'&/-]{5,})",
            1
        )
        full_rs_exact = str_match_first(
            text,
            r"(?is)Denominaci[oó]n\s*/?\s*Raz[oó]n\s*Social\s*:\s*([^\r\n]+)",
            1
        )

        if safe_nzchar(nombres_val):
            out["Nombres"] = s_trim(nombres_val)
            if safe_nzchar(ap1):
                ap1c = s_trim(ap1)
                ap1c = s_trim(re.sub(r"(?is)\s*Segundo\s*Apellido.*$", "", ap1c))
                ap1c = s_trim(re.sub(r"(?is)\s*Fecha\s+inicio\s+de\s+operaciones.*$", "", ap1c))
                out["last_name"] = ap1c
            if safe_nzchar(ap2):
                ap2c = s_trim(ap2)
                ap2c = s_trim(re.sub(r"(?is)\s*Fecha\s+inicio\s+de\s+operaciones.*$", "", ap2c))
                out["second_last_name"] = ap2c
        elif safe_nzchar(full_rs_val):
            out["Nombres"] = s_trim(full_rs_val)

        f_ini = str_match_first(
            text,
            r"(?i)(?:Fecha\s*inicio\s*de\s*operaciones|Fechainiciodeoperaciones)[:\s]*([0-9]{1,2}\s*DE\s*[A-ZÁÉÍÓÚÑ]+\s*DE\s*\d{4})",
            1
        )
        if safe_nzchar(f_ini):
            out["created_at"] = normalize_date_es(f_ini)

        # Prefer the emission date (Lugar y Fecha de Emisión) when present
        f_emision = str_match_first(
            text,
            r"(?is)Lugar\s+y\s+Fecha\s+de\s+Emisi[oó]n.*?A\s+([0-9]{1,2}\s*DE\s*[A-ZÁÉÍÓÚÑ]+\s*DE\s*\d{4})",
            1
        )
        if safe_nzchar(f_emision):
            out["created_at"] = normalize_date_es(f_emision)

        cp = str_match_first(text, r"(?i)(C[oó]digo\s*Postal|C\.?P\.?)[:\s]*([0-9]{5})", 2)
        if safe_nzchar(cp):
            out["codigo_postal"] = cp

        vial = str_match_first(
            text,
            r"(?is)(?:Nombre\s+de\s+Vialidad)[:\s]*([^\n\r]{3,}?)(?=\s*(?:"
            r"N[úu]mero\s*Exterior|N[úu]mero\s*Interior|Nombre\s+de\s+la\s+Colonia|"
            r"Nombre\s+de\s+la\s+Localidad|Nombre\s+del\s+Municipio|Demarcaci[oó]n\s+Territorial|"
            r"Nombre\s+de\s+la\s+Entidad\s+Federativa|Entre\s+Calle|Y\s+Calle|"
            r"Correo\s+Electr[oó]nico|Tel\.?\s*Fijo|Actividades?\s+Econ[oó]micas?|$))",
            1
        )

        if not safe_nzchar(vial):
            vial = str_match_first(
                text,
                r"(?is)(?:Vialidad|Calle)[:\s]*([^\n\r]{3,}?)(?=\s*(?:"
                r"N[úu]mero\s*Exterior|N[úu]mero\s*Interior|Nombre\s+de\s+la\s+Colonia|"
                r"Nombre\s+de\s+la\s+Localidad|Nombre\s+del\s+Municipio|Demarcaci[oó]n\s+Territorial|"
                r"Nombre\s+de\s+la\s+Entidad\s+Federativa|Entre\s+Calle|Y\s+Calle|"
                r"Correo\s+Electr[oó]nico|Tel\.?\s*Fijo|Actividades?\s+Econ[oó]micas?|$))",
                1
            )
            if safe_nzchar(vial) and re.search(r"(?i)Nombre\s+de\s+Vialidad\s*:", vial):
                vial = re.sub(r"(?is)^.*?Nombre\s+de\s+Vialidad\s*:\s*", "", vial)

        if safe_nzchar(vial):
            out["nombre_vialidad"] = cut_after_label_noise(vial)

        numext = str_match_first(
            text,
            r"(?is)N[úu]mero\s*Exterior[:\s]*([^\n\r]{1,40}?)(?=\s*(?:"
            r"N[úu]mero\s*Interior|Nombre\s+de\s+la\s+Colonia|Colonia|Nombre\s+de\s+la\s+Localidad|"
            r"Nombre\s+del\s+Municipio|Demarcaci[oó]n\s+Territorial|Nombre\s+de\s+la\s+Entidad\s+Federativa|"
            r"Entre\s+Calle|Y\s+Calle|Correo\s+Electr[oó]nico|Tel\.?\s*Fijo|Actividades?\s+Econ[oó]micas?|$))",
            1
        )
        if safe_nzchar(numext):
            out["numero_exterior"] = s_trim(numext)

        raw_int = str_match_first(
            text,
            r"(?is)N[úu]mero\s*Interior[:\s]*([^\n\r]{0,40}?)(?=\s*(?:"
            r"Nombre\s+de\s+la\s+Colonia|Colonia|Nombre\s+de\s+la\s+Localidad|"
            r"Nombre\s+del\s+Municipio|Demarcaci[oó]n\s+Territorial|"
            r"Nombre\s+de\s+la\s+Entidad\s+Federativa|Entre\s+Calle|Y\s+Calle|"
            r"Correo\s+Electr[oó]nico|Tel\.?\s*Fijo|Actividades?\s+Econ[oó]micas?|$))",
            1
        )
        if safe_nzchar(raw_int):
            ni = s_trim(raw_int)
            if (not ni) or re.search(r"(?i)^Nombre(\b|\s)", ni):
                ni = None
            out["numero_interior"] = ni

        ent = str_match_first(
            text,
            r"(?is)(Nombre\s+del\s+Municipio\s+o\s+Demarcaci[oó]n\s+Territorial|Municipio|Demarcaci[oó]n\s*Territorial)[:\s]*([A-ZÁÉÍÓÚÑ .'-]{3,})",
            2
        )
        mun = ent
        col = str_match_first(
            text,
            r"(?i)(Nombre\s+de\s+la\s+Colonia|Colonia)[:\s]*([A-ZÁÉÍÓÚÑ 0-9.'-]{3,})",
            2
        )
        if safe_nzchar(mun):
            out["municipality"] = truncate_before_NOMBRE(s_trim(mun))
        if safe_nzchar(col):
            out["neighborhood"] = truncate_before_NOMBRE(s_trim(col))

        if not safe_nzchar(out.get("nombre_vialidad")):
            vial2 = str_match_first(text, r"(?i)(?:Nombre\s*de\s*Vialidad|Vialidad|Calle)[:\s]*([^\n\r,]{3,})", 1)
            if safe_nzchar(vial2):
                out["nombre_vialidad"] = cut_after_label_noise(vial2)

        out["nationality"] = "mexicana"
        out["clave_pais"] = "MX"
        out["contact_email"] = coalesce(extract_email(text), None)
        out["contact_phone"] = coalesce(extract_phone(text), None)

        out["industry"] = extract_actividades_top(text, logfun)
        out["industry_SAT"] = out["industry"]

        dob = birthday_from_rfc(out.get("RFC"))
        if not safe_nzchar(dob):
            dob = birthday_from_curp(out.get("curp"))
        if safe_nzchar(dob):
            out["birthday_at"] = dob

        if callable(logfun):
            for k in TARGET_COLS:
                logfun(f"    [csf] {k}: {out.get(k) or ''}")

    except Exception as e:
        if callable(logfun):
            logfun("  ERROR parse_csf_fields:", str(e))

    tipo = tipo_persona_from_rfc(out.get("RFC"))
    if tipo is None:
        is_pf = safe_nzchar(out.get("last_name")) or safe_nzchar(out.get("second_last_name"))
        if is_pf:
            tipo = "fisica"
        elif safe_nzchar(out.get("Nombres")):
            tipo = "moral"
        else:
            tipo = "desconocido"

    if tipo == "moral":
        name_raw = full_rs_exact if safe_nzchar(full_rs_exact) else full_rs_val
        if safe_nzchar(name_raw):
            name_clean = re.sub(r"(?is)\s*R[ée]gimen\s+Capital.*$", "", name_raw)
            out["Nombres"] = s_trim(name_clean)
        out["last_name"] = None
        out["second_last_name"] = None

    if tipo == "fisica":
        if safe_nzchar(out.get("Nombres")):
            out["Nombres"] = s_trim(re.sub(r"(?is)\s*Primer\s*Apellido.*$", "", out["Nombres"]))
        if safe_nzchar(out.get("last_name")):
            out["last_name"] = s_trim(re.sub(r"(?is)\s*Segundo\s*Apellido.*$", "", out["last_name"]))
            out["last_name"] = s_trim(re.sub(r"(?is)\s*Fecha\s+inicio\s+de\s+operaciones.*$", "", out["last_name"]))
        if safe_nzchar(out.get("second_last_name")):
            out["second_last_name"] = s_trim(re.sub(r"(?is)\s*Fecha\s+inicio\s+de\s+operaciones.*$", "", out["second_last_name"]))

    return {"tipo": tipo, "row": out}

def parse_cfdi_fields(text: str, logfun=None) -> Dict[str, Any]:
    out = empty_row_vec()
    try:
        rfc = (
            str_match_first(text, r"(?i)RFC\s*(del)?\s*Receptor[:\s]*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3})", 2)
            or str_match_first(text, r"(?i)Receptor.*?RFC[:\s]*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3})", 1)
            or str_match_first(text, r"(?i)RFC\s*[:\s]*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3})", 1)
        )
        if safe_nzchar(rfc):
            out["RFC"] = str(rfc).upper()

        nom = (
            str_match_first(text, r"(?i)Nombre\s*(del)?\s*Receptor[:\s]*([A-ZÁÉÍÓÚÑ0-9 .,'-]{3,})", 2)
            or str_match_first(text, r"(?i)Receptor.*?Nombre[:\s]*([A-ZÁÉÍÓÚÑ0-9 .,'-]{3,})", 1)
        )
        if safe_nzchar(nom):
            out["Nombres"] = s_trim(nom)

        cp = str_match_first(text, r"(?i)(C[oó]digo\s*Postal|C\.?P\.?|Lugar\s+de\s+expedici[oó]n)[:\s]*([0-9]{5})", 2)
        if safe_nzchar(cp):
            out["codigo_postal"] = cp

        ent = str_match_first(text, r"(?i)(Estado|Entidad|Provincia)[:\s]*([A-ZÁÉÍÓÚÑ .'-]{3,})", 2)
        mun = str_match_first(text, r"(?i)(Municipio|Delegaci[oó]n)[:\s]*([A-ZÁÉÍÓÚÑ .'-]{3,})", 2)
        col = str_match_first(text, r"(?i)(Colonia)[:\s]*([A-ZÁÉÍÓÚÑ 0-9.'-]{3,})", 2)
        if safe_nzchar(ent):
            out["province"] = s_trim(ent)
        if safe_nzchar(mun):
            out["municipality"] = s_trim(mun)
        if safe_nzchar(col):
            out["neighborhood"] = s_trim(col)

        vial = str_match_first(text, r"(?i)(Nombre\s*de\s*Vialidad|Calle|Vialidad)[:\s]*([^\n\r,]{3,})", 2)
        if safe_nzchar(vial):
            out["nombre_vialidad"] = cut_after_label_noise(vial)

        numext = str_match_first(
            text,
            r"(?is)((?:No\.?\s*Ext\.?|N[úu]mero\s*Exterior))[:\s]*([^\n\r]{1,40}?)(?=\s*(?:"
            r"(?:No\.?\s*Int\.?|N[úu]mero\s*Interior)|Colonia|C[oó]digo\s*Postal|C\.?P\.?|"
            r"Lugar\s+de\s+expedici[oó]n|Municipio|Delegaci[oó]n|Estado|Entidad|Provincia|$))",
            2
        )
        numint = str_match_first(
            text,
            r"(?is)((?:No\.?\s*Int\.?|N[úu]mero\s*Interior))[:\s]*([^\n\r]{0,40}?)(?=\s*(?:Colonia|C[oó]digo\s*Postal|C\.?P\.?|"
            r"Lugar\s+de\s+expedici[oó]n|Municipio|Delegaci[oó]n|Estado|Entidad|Provincia|$))",
            2
        )
        if safe_nzchar(numext):
            out["numero_exterior"] = s_trim(numext)
        if safe_nzchar(numint):
            out["numero_interior"] = s_trim(numint) if numint else None

        out["contact_email"] = coalesce(extract_email(text), None)
        out["contact_phone"] = coalesce(extract_phone(text), None)
        out["nationality"] = "mexicana"
        out["clave_pais"] = "MX"

        curp = str_match_first(text, r"(?i)CURP[:\s]*([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2})", 1)
        if safe_nzchar(curp):
            out["curp"] = str(curp).upper()

        dob = birthday_from_rfc(out.get("RFC"))
        if not safe_nzchar(dob):
            dob = birthday_from_curp(out.get("curp"))
        if safe_nzchar(dob):
            out["birthday_at"] = dob

        if callable(logfun):
            for k in TARGET_COLS:
                logfun(f"    [cfdi] {k}: {out.get(k) or ''}")

    except Exception as e:
        if callable(logfun):
            logfun("  ERROR parse_cfdi_fields:", str(e))

    tipo = tipo_persona_from_rfc(out.get("RFC"))
    if tipo is None:
        tipo = "fisica"
    return {"tipo": tipo, "row": out}

def detect_doc_type(text: str) -> str:
    t = (text or "").upper()
    is_csf = bool(re.search(r"CONSTANCIA DE SITUACI[OÓ]N FISCAL|C[ÉE]DULA DE IDENTIFICACI[OÓ]N FISCAL|SERVICIO DE ADMINISTRACI[OÓ]N TRIBUTARIA", t))
    is_cfdi = bool(re.search(r"COMPROBANTE FISCAL DIGITAL|CFDI|FACTURA|USO CFDI|RECEPTOR|EMISOR", t))
    if is_csf:
        return "csf"
    if is_cfdi:
        return "cfdi"
    return "csf"

def process_one_doc(pdf_path: str, use_ocr: bool = False, logfun=lambda *args: None) -> Dict[str, Any]:
    txt = clean_text(extract_pdf_text(pdf_path, use_ocr=use_ocr))
    logfun(f"  Texto extraído: {len(txt)} chars")
    logfun("  OCR:", "ON" if use_ocr else "OFF")
    logfun("  Snippet:", (txt[:DIAG_MAX] if txt else ""))
    if not safe_nzchar(txt):
        return {"tipo": "desconocido", "row": empty_row_vec()}
    doc_type = detect_doc_type(txt)
    logfun("  Tipo detectado:", doc_type)
    try:
        if doc_type == "csf":
            return parse_csf_fields(txt, logfun)
        return parse_cfdi_fields(txt, logfun)
    except Exception as e:
        logfun("  ERROR parser:", str(e))
        return {"tipo": "desconocido", "row": empty_row_vec()}

# =============================================================================
# Streamlit App (UI mapping from Shiny)
# =============================================================================

st.set_page_config(page_title="Generar Excel desde CSF/CFDI (SAT)", layout="wide")
st.title("Generar Excel desde CSF/CFDI (SAT)")

catalogs = load_sat_catalogs()

if "logs" not in st.session_state:
    st.session_state.logs = ""
if "status" not in st.session_state:
    st.session_state.status = "Listo."
if "fisica" not in st.session_state:
    st.session_state.fisica = None
if "moral" not in st.session_state:
    st.session_state.moral = None
if "dirfiles" not in st.session_state:
    st.session_state.dirfiles = pd.DataFrame(columns=["datapath", "name"])

def logf(*args):
    st.session_state.logs += ("\n" if st.session_state.logs else "") + " ".join(str(a) for a in args)

with st.sidebar:
    st.header("Entradas")
    uploaded = st.file_uploader("Sube PDF (múltiples)", type=["pdf"], accept_multiple_files=True)

    st.markdown("---")
    st.subheader("Carpeta raíz (opcional)")
    st.caption("Se leerán recursivamente solo PDFs cuyo nombre empiece con CSF_SUSCRIPTOR.")
    dir_path = st.text_input("Ruta de carpeta raíz", value="")
    scan_dir = st.button("Escanear carpeta")

    use_ocr = st.checkbox("Usar OCR si es necesario", value=False)

    st.markdown("---")
    go = st.button("Generar Excel", type="primary")

    st.markdown("---")
    st.subheader("Logs")
    st.caption("(cópialos si algo falla)")
    st.text_area("logs", value=st.session_state.logs, height=240)

    st.markdown("---")
    st.write(st.session_state.status)

def scan_directory(root: str) -> pd.DataFrame:
    if not root:
        return pd.DataFrame(columns=["datapath", "name"])
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return pd.DataFrame(columns=["datapath", "name"])
    matches = []
    rx = re.compile(r"^CSF_SUSCRIPTOR.*\.pdf$", flags=re.IGNORECASE)
    for base, _, files in os.walk(root):
        for fn in files:
            if rx.match(fn):
                full = os.path.join(base, fn)
                matches.append((full, os.path.basename(full)))
    return pd.DataFrame(matches, columns=["datapath", "name"])

if scan_dir:
    try:
        st.session_state.status = "Escaneando carpeta..."
        logf("→ [Carpeta] Seleccionada:", dir_path)
        df = scan_directory(dir_path)
        if df.empty:
            st.session_state.dirfiles = df
            logf("  × No se encontraron PDFs que coincidan con ^CSF_SUSCRIPTOR.*\\.pdf$")
        else:
            st.session_state.dirfiles = df
            logf(f"  ✓ {len(df)} PDF(s) agregados desde carpeta (recursivo).")
        st.session_state.status = "Listo. Carpeta escaneada."
    except Exception as e:
        logf("  ERROR escaneando carpeta:", str(e))
        st.session_state.status = "Error escaneando carpeta."

def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=TARGET_COLS)

def as_char_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None:
        return empty_df()
    out = df.copy()
    for nm in out.columns:
        out[nm] = out[nm].astype(str)
        out.loc[out[nm].isin(["None", "nan", "NaN"]), nm] = ""
    return out

def add_industry_sat(df: Optional[pd.DataFrame], tipo_label: str) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return df
    if "industry" not in df.columns:
        df = df.copy()
        df["industry_SAT"] = None
        return df
    df = df.copy()
    df["industry_SAT"] = [
        match_industry_to_sat(ind, tipo_label, catalogs) for ind in df["industry"].tolist()
    ]
    return df

def to_df(lst: List[Dict[str, Optional[str]]]) -> pd.DataFrame:
    if not lst:
        return empty_df()
    return pd.DataFrame(lst, columns=TARGET_COLS)

def collect_files(uploaded_files) -> Tuple[pd.DataFrame, List[str]]:
    """
    Returns:
      files_df: columns datapath,name
      tmp_paths: list of temp file paths to delete later
    """
    tmp_paths = []
    rows = []

    if uploaded_files:
        for uf in uploaded_files:
            # Save to temp path (pdfplumber/pdf2image need paths)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(uf.getbuffer())
            tmp.flush()
            tmp.close()
            tmp_paths.append(tmp.name)
            rows.append((tmp.name, uf.name))

    if isinstance(st.session_state.dirfiles, pd.DataFrame) and not st.session_state.dirfiles.empty:
        for _, r in st.session_state.dirfiles.iterrows():
            rows.append((str(r["datapath"]), str(r["name"])))

    files_df = pd.DataFrame(rows, columns=["datapath", "name"])
    return files_df, tmp_paths

if go:
    st.session_state.logs = ""
    st.session_state.status = "Procesando documentos..."

    fis_rows: List[Dict[str, Optional[str]]] = []
    mor_rows: List[Dict[str, Optional[str]]] = []

    files_df, tmp_paths = collect_files(uploaded)

    try:
        if not files_df.empty:
            progress = st.progress(0)
            for i, row in enumerate(files_df.itertuples(index=False), start=1):
                path = row.datapath
                nm = row.name
                st.session_state.status = f"Procesando PDF: {nm}"
                logf("→ [PDF]", nm)

                try:
                    res = process_one_doc(path, use_ocr=bool(use_ocr), logfun=logf)
                except Exception as e:
                    logf("  ERROR:", str(e))
                    res = {"tipo": "desconocido", "row": empty_row_vec()}

                is_empty = row_is_empty(res["row"])
                logf("  Fila vacía?:", is_empty)
                if is_empty and (not use_ocr):
                    logf("  Reintento con OCR=TRUE (fila vacía).")
                    try:
                        res2 = process_one_doc(path, use_ocr=True, logfun=logf)
                        res = res2
                    except Exception as e:
                        logf("  ERROR (OCR):", str(e))
                    is_empty = row_is_empty(res["row"])
                    logf("  Fila vacía tras OCR?:", is_empty)

                if res.get("tipo") == "moral":
                    mor_rows.append(res["row"])
                else:
                    fis_rows.append(res["row"])

                progress.progress(int(i / len(files_df) * 100))

        st.session_state.fisica = as_char_df(to_df(fis_rows))
        st.session_state.moral = as_char_df(to_df(mor_rows))

        st.session_state.fisica = add_industry_sat(st.session_state.fisica, "fisica")
        st.session_state.moral = add_industry_sat(st.session_state.moral, "moral")

        pf = 0 if st.session_state.fisica is None else len(st.session_state.fisica)
        pm = 0 if st.session_state.moral is None else len(st.session_state.moral)

        logf(f"  Filas agregadas → PF: {pf} | PM: {pm}")
        st.session_state.status = f"Listo. Personas Físicas: {pf} | Personas Morales: {pm}"

    finally:
        # cleanup temp uploads
        for p in tmp_paths:
            try:
                os.unlink(p)
            except Exception:
                pass

# Preview (first rows)
def add_tipo(df: pd.DataFrame, tipo_label: str) -> pd.DataFrame:
    if df is None or df.empty:
        return empty_df()
    out = df.copy()
    out.insert(0, "tipo", tipo_label)
    return out

fis = add_tipo(st.session_state.fisica if st.session_state.fisica is not None else empty_df(), "Persona Física")
mor = add_tipo(st.session_state.moral if st.session_state.moral is not None else empty_df(), "Persona Moral")
preview = pd.concat([fis, mor], ignore_index=True).head(10)

st.subheader("Resumen (primeras filas)")
st.dataframe(preview, use_container_width=True, height=260)

# Download Excel
def make_excel_bytes() -> bytes:
    fis_df = st.session_state.fisica if st.session_state.fisica is not None else empty_df()
    mor_df = st.session_state.moral if st.session_state.moral is not None else empty_df()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        fis_df.to_excel(writer, sheet_name="Persona Física", index=False)
        mor_df.to_excel(writer, sheet_name="Persona Moral", index=False)
    return output.getvalue()

filename = f"csf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
st.download_button(
    "Descargar Excel (.xlsx)",
    data=make_excel_bytes(),
    file_name=filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
