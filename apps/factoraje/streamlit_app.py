# --- bootstrap so local imports (factoraje_logic.py) work on Streamlit Cloud ---
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# ---------------------------------------------------------------------------


import re

import streamlit as st
import pandas as pd
from datetime import timedelta

from factoraje_logic import (
    INTERVAL_DEFS,
    is_rfc,
    today_utc,
    list_invoices_headers_api,
    headers_from_xml,
    metrics_by_interval,
    build_excel_for_rfcs,
    get_api_mon,
)

st.set_page_config(page_title="Factoraje - Proveedores por intervalo", layout="wide")

st.title("Proveedores principales por RFC con columnas por intervalo")

# Sidebar inputs (mirrors Shiny controls)
with st.sidebar:
    environment = st.selectbox("Environment", options=["sandbox", "production"], index=0)
    source = st.radio("Fuente", options=[("api", "API (facturas)"), ("xml", "XML")], format_func=lambda x: x[1])
    source_key = source[0]

    api_key = st.text_input("API Key (X-API-Key)", type="password", help="Si lo dejas vacío, intenta usar SYNTAGE_API_KEY del entorno.")
    rfcs_text = st.text_area("RFC(s) (uno por línea o separados por coma)", height=140)

    intervals = st.multiselect("Intervalos", options=list(INTERVAL_DEFS.keys()), default=list(INTERVAL_DEFS.keys()))
    excluir_fx = st.checkbox("Excluir facturas con tipo de cambio desconocido (no MXN)", value=True)

    preview_btn = st.button("Vista previa (primer RFC)")
    excel_btn = st.button("Generar Excel (todos los RFCs)")

base_url = "https://api.sandbox.syntage.com" if environment == "sandbox" else "https://api.syntage.com"

# Parse RFCs
raw = rfcs_text or ""
parts = [p.strip().upper() for p in re.split(r"[\s,;\n\r]+", raw) if p.strip()]
rfcs = []
for p in parts:
    p2 = re.sub(r"[^A-Z0-9]", "", p)
    if is_rfc(p2):
        if p2 not in rfcs:
            rfcs.append(p2)

if not api_key:
    import os
    api_key = os.getenv("SYNTAGE_API_KEY", "")

# Status panel
mon = get_api_mon()
if mon.get("last_status") is not None:
    st.caption(f"Última llamada a Syntage: status={mon.get('last_status')} — {mon.get('last_url')}")
else:
    st.caption("Aún sin llamadas a Syntage en esta sesión.")

def get_headers(src_key: str, rfc: str, dfrom, dto):
    if src_key == "api":
        return list_invoices_headers_api(base_url, api_key, rfc, dfrom, dto)
    return headers_from_xml(base_url, api_key, rfc, dfrom, dto)

# Preview
if preview_btn:
    if not rfcs:
        st.warning("Ingresa al menos un RFC válido.")
    elif not api_key:
        st.warning("Falta API Key (campo o variable SYNTAGE_API_KEY).")
    elif not intervals:
        st.warning("Selecciona al menos un intervalo.")
    else:
        rfc = rfcs[0]
        max_days = max(INTERVAL_DEFS[i] for i in intervals)
        dto = today_utc()
        dfrom = dto - timedelta(days=max_days)

        with st.spinner(f"Calculando para RFC {rfc}…"):
            h = get_headers(source_key, rfc, dfrom, dto)

        if h is None or h.empty:
            st.warning("Sin datos para el RFC / intervalos.")
        else:
            blocks = []
            for lbl in intervals:
                days_back = INTERVAL_DEFS[lbl]
                start = dto - timedelta(days=days_back)
                b = metrics_by_interval(h, lbl, start, dto, rfc, excluir_fx_desconocido=excluir_fx)
                if b is not None and not b.empty:
                    blocks.append(b)

            if not blocks:
                st.warning("Sin datos tras filtros/intervalos.")
            else:
                out = blocks[0]
                for k in range(1, len(blocks)):
                    out = out.merge(blocks[k], on=["emisor_rfc", "emisor_nombre"], how="outer")

                # Fixed Participación (%) from first interval
                ref_lbl = intervals[0]
                ref_part_col = f"Participación ({ref_lbl})"
                ref_total_col = f"Monto total facturas ({ref_lbl})"
                if ref_part_col in out.columns:
                    out["Participación (%)"] = out[ref_part_col]
                elif ref_total_col in out.columns:
                    ts = float(pd.to_numeric(out[ref_total_col], errors="coerce").sum())
                    out["Participación (%)"] = (out[ref_total_col] / ts) if ts > 0 else 0.0
                else:
                    out["Participación (%)"] = 0.0

                # Order
                if ref_part_col in out.columns:
                    out = out.sort_values(ref_part_col, ascending=False)
                elif ref_total_col in out.columns:
                    out = out.sort_values(ref_total_col, ascending=False)

                show = out.rename(columns={"emisor_rfc": "Proveedor_RFC", "emisor_nombre": "Proveedor_Nombre"})
                st.success(f"OK — filas: {len(show)}")
                st.dataframe(show, use_container_width=True)

# Excel
if excel_btn:
    if not rfcs:
        st.error("Ingresa al menos un RFC válido.")
    elif not api_key:
        st.error("Falta API Key (campo o variable SYNTAGE_API_KEY).")
    elif not intervals:
        st.error("Selecciona al menos un intervalo.")
    else:
        with st.spinner("Generando Excel…"):
            xls_bytes = build_excel_for_rfcs(
                base_url=base_url,
                api_key=api_key,
                rfcs=rfcs,
                source=source_key,
                intervals=intervals,
                excluir_fx=excluir_fx,
            )
        st.download_button(
            "Descargar Excel",
            data=xls_bytes,
            file_name=f"Proveedores_por_intervalo_{today_utc().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
