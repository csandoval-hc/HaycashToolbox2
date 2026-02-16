"""
BBVA Domiciliación Generator – Smart Template Mode (Streamlit)
- Same generation logic as your Tkinter script
- Streamlit UI for Streamlit Cloud
- Outputs latin-1 + CRLF, fixed-length records (default 300 or template length)
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


# =======================
# HELPERS (same logic)
# =======================
def normalize_text(text: str, length: int) -> str:
    """Uppercases, removes special chars, and aligns left."""
    t = str(text or "").upper().strip()
    t = t.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    t = t.replace("Ñ", "N").replace("\n", " ").replace("\r", "")
    return t[:length].ljust(length)


def format_account(cuenta: str, tipo_code: str) -> str:
    """Formats account based on type (01=10, 03=16, 40=18)."""
    digits = "".join(filter(str.isdigit, str(cuenta)))
    if tipo_code == "40":  # CLABE
        return digits[-18:].zfill(20)
    if tipo_code == "03":  # Debit
        return digits[-16:].zfill(20)
    # Cheques
    return digits[-10:].zfill(20)


def infer_tipo_cuenta(cuenta: str) -> str:
    l = len("".join(filter(str.isdigit, str(cuenta))))
    if l >= 18:
        return "40"
    if l >= 16:
        return "03"
    return "01"


# =======================
# FILE PARSER (same logic, but bytes)
# =======================
def parse_template_bytes(template_bytes: bytes) -> dict:
    """
    Reads the valid .exp bytes to extract static header info.
    """
    if not template_bytes:
        return {}

    try:
        lines = template_bytes.splitlines()
        if not lines:
            return {}

        sample_line = lines[0]
        header_str = sample_line.decode("latin-1", errors="ignore")

        return {
            "len": len(sample_line),
            "bank": header_str[11:14],
            "service": header_str[15],
            "name": header_str[60:100],
            "rfc": header_str[100:118],
            "block_prefix": header_str[16:23],
        }
    except Exception as e:
        # Keep behavior: warn but continue with defaults
        st.warning(f"Warning parsing template: {e}")
        return {}


# =======================
# GENERATOR (same logic, returns bytes)
# =======================
def generate_file_bytes(
    excel_bytes: bytes,
    excel_name: str,
    template_bytes: bytes | None,
    fecha_proc: str,
    ref_start: str,
    block_num: str,
) -> tuple[bytes, str]:
    # 1. Defaults (same values)
    config = {
        "len": 300,
        "name": "BANCO ACTINVER SA IBM POR CTA FID 6011",
        "rfc": "PBI*061115SC6     ",  # kept
        "bank": "012",
        "service": "2",
    }

    # 2. Override with Template if provided
    if template_bytes:
        config.update(parse_template_bytes(template_bytes))

    if not fecha_proc:
        fecha_proc = datetime.now().strftime("%Y%m%d")

    # Read dataframe (xlsx vs csv) from bytes
    ext = Path(excel_name).suffix.lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        df = pd.read_excel(BytesIO(excel_bytes), dtype=str)
    else:
        df = pd.read_csv(BytesIO(excel_bytes), dtype=str)

    df = df.fillna("")

    lines: list[str] = []

    # --- HEADER (01) ---
    h_bank = (config.get("bank") or "012")
    h_serv = (config.get("service") or "2")
    h_name = (config.get("name") or "").ljust(40)[:40]
    h_rfc = (config.get("rfc") or "").ljust(18)[:18]
    h_block = str(block_num).zfill(7)

    header = (
        f"01000000130{h_bank}E{h_serv}{h_block}{fecha_proc}0100"
        + (" " * 25)
        + h_name
        + h_rfc
        + (" " * 182)
    )
    header = header[: config["len"]].ljust(config["len"])
    lines.append(header)

    # --- DETAILS (02) ---
    total_amount = 0.0
    ref_count = int(ref_start)

    for idx, row in df.iterrows():
        seq = idx + 2

        try:
            imp = float(str(row.get("Importe", 0)).replace(",", ""))
        except Exception:
            imp = 0.0
        total_amount += imp

        cta = str(row.get("Cuenta cargo", "")).strip()
        tipo_cta = infer_tipo_cuenta(cta)

        banco_raw = str(row.get("Banco", "000")).strip()
        banco_digits = "".join(filter(str.isdigit, banco_raw))
        banco_dest = banco_digits[-3:] if len(banco_digits) >= 3 else "000"

        nombre = normalize_text(row.get("Nombre del cliente", ""), 40)
        ref_alf = normalize_text(row.get("Referencia", ""), 40)
        titular = normalize_text(row.get("Titular del servicio", "HAYCASH"), 40)
        leyenda = ref_alf

        imp_cents = int(round(imp * 100))
        iva_cents = int(round(imp * 0.16 * 100))

        detail = (
            f"02{seq:07d}3001{imp_cents:015d}{fecha_proc}"
            + (" " * 24)
            + f"51{fecha_proc}{banco_dest}{tipo_cta}{format_account(cta, tipo_cta)}"
            + f"{nombre}{ref_alf}{titular}"
            + f"{iva_cents:015d}{ref_count:07d}{leyenda}00"
            + (" " * 21)
        )

        detail = detail[: config["len"]].ljust(config["len"])
        lines.append(detail)
        ref_count += 1

    # --- SUMMARY (09) ---
    last_seq = len(lines) + 1
    total_cents = int(round(total_amount * 100))

    summary = (
        f"09{last_seq:07d}30{h_block}{len(df):07d}{total_cents:018d}"
        + (" " * 257)
    )
    summary = summary[: config["len"]].ljust(config["len"])
    lines.append(summary)

    # Write bytes as latin-1 + CRLF (same behavior)
    out = bytearray()
    for line in lines:
        out += line.encode("latin-1", errors="replace")
        out += b"\r\n"

    used_cfg = "Template" if template_bytes else "Default"
    msg = f"Generado: {len(lines)} registros.\nUsando Configuración: {used_cfg}\nLongitud registro: {config['len']} bytes"
    return bytes(out), msg


# =======================
# STREAMLIT UI
# =======================
def main():
    st.set_page_config(page_title="BBVA Generator - Template Clone Mode", layout="centered")
    st.title("BBVA Generator - Template Clone Mode")

    st.write("1) Sube el Excel/CSV con datos")
    excel_file = st.file_uploader("Archivo Excel/CSV (Datos)", type=["xlsx", "xls", "xlsm", "csv"])

    st.write("2) (Opcional) Sube archivo muestra/template (.exp) para copiar Header/RFC")
    template_file = st.file_uploader("Archivo Template (.exp)", type=["exp"])

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha = st.text_input("Fecha (AAAAMMDD)", value=datetime.now().strftime("%Y%m%d"))
    with col2:
        ref_start = st.text_input("Ref. Numérica Inicial", value="1")
    with col3:
        block_num = st.text_input("Bloque", value="1")

    st.divider()

    if st.button("GENERAR ARCHIVO", type="primary", disabled=excel_file is None):
        if excel_file is None:
            st.error("Falta archivo Excel/CSV.")
            return

        try:
            excel_bytes = excel_file.getvalue()
            template_bytes = template_file.getvalue() if template_file else None

            out_bytes, msg = generate_file_bytes(
                excel_bytes=excel_bytes,
                excel_name=excel_file.name,
                template_bytes=template_bytes,
                fecha_proc=fecha.strip(),
                ref_start=ref_start.strip() or "1",
                block_num=block_num.strip() or "1",
            )

            st.success(msg)

            out_name = f"{Path(excel_file.name).stem}_BBVA.txt"
            st.download_button(
                label="Descargar TXT",
                data=out_bytes,
                file_name=out_name,
                mime="text/plain",
            )

        except Exception as e:
            st.exception(e)


if __name__ == "__main__":
    main()
