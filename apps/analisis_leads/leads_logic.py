"""
Analisis Leads - Streamlit port (logic kept from Shiny app)

Key behaviors preserved:
- Reads snapshot from CSV (data/snapshot.csv) and reviewed marks from CSV (data/reviewed_leads_app.csv)
- If snapshot is missing "concentracion_12meses", retries direct read; otherwise creates empty col
- Normalizes snapshot to the same columns used by the app
- Excludes RFCs in www/cat_credit_id_rfc.csv (normalized A-Z/0-9)
- Enriched view:
  - persona_tipo inferred from RFC length when present
  - money columns formatted as strings (or NA)
  - reviewed_by + revisado flag merged from reviewed table
- Filters:
  - allowed statuses list
  - hard cutoff to last 90 days (created_mx) while keeping NAs
  - pending tab applies date range filter; reviewed tab doesn't (same as Shiny)
  - status multiselect applies to both
- Mark reviewed writes to reviewed csv (append/update)
- Reset reviewed clears reviewed csv (admin only)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import date, datetime, timedelta
import re
import os
import pandas as pd
import numpy as np

ALLOWED_STATUSES = [
    "Lead calificado",
    "Oferta generada",
    "Oferta enviada",
    "Oferta aceptada",
    "En espera de documentos",
    "No perfila",
    "Comité",
]

DEFAULT_REVIEWED_CSV = Path("data") / "reviewed_leads_app.csv"
DEFAULT_SNAPSHOT_CSV = Path("data") / "snapshot.csv"
WWW_DIR = Path("www")


def safe_read_csv(path: str | Path) -> pd.DataFrame | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        # try utf-8-sig first (handles BOM), fallback to latin-1
        try:
            return pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(p, dtype=str, encoding="latin-1")
    except Exception:
        return None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_rfc(x: object) -> str:
    s = "" if x is None else str(x)
    s = s.replace("\ufeff", "")
    s = s.strip().upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def parse_cmx(x: object) -> datetime | None:
    """
    Shiny app uses parse_cmx() from utils; here we accept common formats:
    - ISO-like
    - "YYYY-mm-dd"
    - "dd/mm/YYYY"
    - "YYYY-mm-dd HH:MM:SS"
    """
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    # normalize timezone suffixes and commas
    s = s.replace("\ufeff", "").strip()

    fmts = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            pass
    # last resort: pandas parse
    try:
        ts = pd.to_datetime(s, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.to_pydatetime()
    except Exception:
        return None


def fmt_money_or_na(x: object) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        v = float(s)
    except Exception:
        return None
    # mimic a simple money formatting used in the Shiny app (string output)
    return f"{v:,.2f}"


@dataclass
class ReviewStore:
    path: Path

    def read_or_empty(self) -> pd.DataFrame:
        df = safe_read_csv(self.path)
        if df is None or df.empty:
            return pd.DataFrame({"lead_id": pd.Series(dtype=str), "reviewed_by": pd.Series(dtype=str)})
        # keep exact columns like server.R transmute
        out = pd.DataFrame({
            "lead_id": df.get("lead_id", pd.Series(dtype=str)).astype(str),
            "reviewed_by": df.get("reviewed_by", pd.Series(dtype=str)).astype(str),
        })
        out["lead_id"] = out["lead_id"].astype(str)
        out["reviewed_by"] = out["reviewed_by"].replace({"nan": ""}).astype(str)
        out = out[out["lead_id"].astype(str).str.len() > 0]
        return out

    def mark(self, lead_ids: list[str], reviewer: str) -> None:
        ensure_parent(self.path)
        cur = self.read_or_empty()
        lead_ids = [str(x) for x in lead_ids]
        # update existing and append new
        mapping = dict(zip(lead_ids, [reviewer] * len(lead_ids)))
        if not cur.empty:
            cur.loc[cur["lead_id"].isin(lead_ids), "reviewed_by"] = reviewer
        missing = [lid for lid in lead_ids if cur.empty or (lid not in set(cur["lead_id"].tolist()))]
        if missing:
            add = pd.DataFrame({"lead_id": missing, "reviewed_by": [reviewer] * len(missing)})
            cur = pd.concat([cur, add], ignore_index=True)
        # write
        cur.to_csv(self.path, index=False)

    def reset(self) -> None:
        ensure_parent(self.path)
        pd.DataFrame({"lead_id": [], "reviewed_by": []}).to_csv(self.path, index=False)


@dataclass
class SnapshotSource:
    path: Path

    def read_or_empty(self) -> pd.DataFrame:
        df = safe_read_csv(self.path)
        if df is None:
            return pd.DataFrame()
        return df.fillna("")


def load_blocked_rfcs(www_dir: Path = WWW_DIR) -> set[str]:
    p = www_dir / "cat_credit_id_rfc.csv"
    if not p.exists():
        return set()
    df = safe_read_csv(p)
    if df is None or df.empty:
        return set()

    # match R logic to pick RFC column with BOM/spacing handling
    cols_clean = [str(c).replace("\ufeff", "").strip().lower() for c in df.columns]
    idx = None
    if "rfc" in cols_clean:
        idx = cols_clean.index("rfc")
    else:
        for i, c in enumerate(cols_clean):
            if "rfc" in c:
                idx = i
                break
    if idx is None:
        # pick column with most non-empty RFC-like values
        counts = []
        for c in df.columns:
            vals = df[c].astype(str).map(normalize_rfc)
            counts.append(int((vals != "").sum()))
        idx = int(np.argmax(counts)) if counts else 0

    vals = df.iloc[:, idx].astype(str).map(normalize_rfc)
    blocked = set(v for v in vals.unique().tolist() if v)
    return blocked


def build_snapshot_view(snapshot_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Mirror the server.R normalization/transmute into the columns the app uses.
    """
    if snapshot_raw is None or snapshot_raw.empty:
        return pd.DataFrame(columns=[
            "Lead_id","nombre","rfc","giro","broker","analista","estatus_optools","persona_tipo",
            "lost_reason_name","ventas_tpv","depositos","venta_facturada","monto_creditos_abiertos",
            "deuda_vencida_buro","created_mx","concentracion_12meses"
        ])

    # ensure concentracion_12meses exists
    if "concentracion_12meses" not in snapshot_raw.columns:
        snapshot_raw["concentracion_12meses"] = ""

    def col(name: str, default=""):
        return snapshot_raw[name] if name in snapshot_raw.columns else default

    out = pd.DataFrame({
        "Lead_id": col("lead_id", "").astype(str),
        "nombre": col("nombre", ""),
        "rfc": col("rfc", ""),
        "giro": col("giro", ""),
        "broker": col("broker", ""),
        "analista": col("analista", ""),
        "estatus_optools": col("estatus_optools", ""),
        "persona_tipo": col("persona_tipo", ""),
        "lost_reason_name": col("lost_reason_name", ""),
        "ventas_tpv": pd.to_numeric(col("ventas_tpv", ""), errors="coerce"),
        "depositos": pd.to_numeric(col("depositos", ""), errors="coerce"),
        "venta_facturada": pd.to_numeric(col("venta_facturada", ""), errors="coerce"),
        "monto_creditos_abiertos": pd.to_numeric(col("monto_creditos_abiertos", ""), errors="coerce"),
        "deuda_vencida_buro": pd.to_numeric(col("deuda_vencida_buro", ""), errors="coerce"),
        "created_mx": col("created_mx", ""),
        "concentracion_12meses": col("concentracion_12meses", "").astype(str),
    })
    return out


def enrich(snapshot: pd.DataFrame, reviewed_tbl: pd.DataFrame) -> pd.DataFrame:
    rev_ids = set(reviewed_tbl["lead_id"].astype(str).tolist()) if reviewed_tbl is not None and not reviewed_tbl.empty else set()
    rev_map = {}
    if reviewed_tbl is not None and not reviewed_tbl.empty:
        rev_map = dict(zip(reviewed_tbl["lead_id"].astype(str), reviewed_tbl["reviewed_by"].astype(str)))

    df = snapshot.copy()

    # persona_tipo inference
    rfc_series = df.get("rfc", pd.Series([""] * len(df))).fillna("").astype(str)
    df["persona_tipo"] = np.where(
        rfc_series.str.len() == 13, "PF",
        np.where(rfc_series.str.len() == 12, "PM", df.get("persona_tipo", "").astype(str).replace({"": "NA"}))
    )

    # money formatting to strings
    for c in ["ventas_tpv","depositos","venta_facturada","monto_creditos_abiertos","deuda_vencida_buro"]:
        if c in df.columns:
            df[c] = df[c].apply(fmt_money_or_na)

    df["reviewed_by"] = df["Lead_id"].astype(str).map(lambda x: rev_map.get(x, None))
    df["is_reviewed"] = df["Lead_id"].astype(str).isin(rev_ids)
    df["revisado"] = df["is_reviewed"].astype(int)

    # select column order (same as dplyr::select in server.R)
    keep = [
        "nombre","rfc","broker","analista",
        "ventas_tpv","depositos","venta_facturada",
        "estatus_optools","lost_reason_name","persona_tipo",
        "monto_creditos_abiertos","deuda_vencida_buro",
        "created_mx","concentracion_12meses",
        "reviewed_by","revisado","giro","Lead_id"
    ]
    for k in keep:
        if k not in df.columns:
            df[k] = None
    return df[keep]


def apply_filters(df: pd.DataFrame, reviewed: bool, created_range: tuple[date, date] | None, statuses: list[str] | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=df.columns if df is not None else None)

    out = df.copy()

    # keep only allowed statuses (for both tabs)
    if "estatus_optools" in out.columns:
        out = out[out["estatus_optools"].isin(ALLOWED_STATUSES)]

    # hard cutoff 90 days (keeping NAs)
    if "created_mx" in out.columns:
        cmx_dt = out["created_mx"].apply(parse_cmx)
        cmx_date = cmx_dt.apply(lambda d: d.date() if d else None)
        cutoff = date.today() - timedelta(days=90)
        keep_mask = cmx_date.isna() | (cmx_date >= cutoff)
        out = out[keep_mask].copy()

        cmx_dt = out["created_mx"].apply(parse_cmx)
        cmx_date = cmx_dt.apply(lambda d: d.date() if d else None)

        # user range only for pending tab
        if (not reviewed) and created_range is not None:
            start, end = created_range
            if start and end:
                keep2 = (~cmx_date.isna()) & (cmx_date >= start) & (cmx_date <= end)
                out = out[keep2].copy()

    # user status selection
    if statuses is not None:
        out = out[out["estatus_optools"].isin(statuses)]

    return out


def kpis(enriched_df: pd.DataFrame, created_range: tuple[date, date] | None, statuses: list[str] | None) -> dict[str, str]:
    df = enriched_df.copy()
    if df.empty:
        return {"pending": "0", "reviewed": "0", "conv": "0%"}

    # date filter (kpis follow pending range)
    if created_range is not None:
        start, end = created_range
        cmx_dt = df["created_mx"].apply(parse_cmx)
        cmx_date = cmx_dt.apply(lambda d: d.date() if d else None)
        df = df[(~cmx_date.isna()) & (cmx_date >= start) & (cmx_date <= end)].copy()

    # status filter
    if statuses is not None:
        df = df[(df["estatus_optools"].isin(statuses)) | (df["estatus_optools"].isna())].copy()

    p = int((df["revisado"] == 0).sum())
    r = int((df["revisado"] == 1).sum())
    t = p + r
    conv = "0%" if t == 0 else f"{round(r / t * 100, 1)}%"
    return {"pending": str(p), "reviewed": str(r), "conv": conv}
