#!/usr/bin/env python3
"""
BBVA Domiciliación – byte-stable fixed-width output (300 BYTES per record)

THIS VERSION RESTORES YOUR ORIGINAL EXTRACTION LOGIC:
- DOES NOT require any specific Excel column to exist
- Uses your same defaults and `.get(...)` behavior
- Keeps your sequencing, ref_counter behavior, IVA calc, etc.
- Still enforces:
  - latin-1 single-byte encoding
  - CRLF
  - EXACTLY 300 bytes per record

Layout corrections kept:
- Header: RFC written in its own 18-char field (still shows your same RFC)
- Header: block written as 7 digits (BBVA requires 7)
- Summary: operation code 30, block matches header, total = SUM(importe) cents
"""
import pandas as pd
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

# =======================
# CONSTANTS (FROM YOUR ORIGINAL CODE)
# =======================
BUSINESS_EMISOR_STR = "BANCO ACTINVER SA IBM POR CTA FID 6011  PBI*061115SC6"
RFC_EMISOR_DEFAULT  = "PBI*061115SC6"
TITULAR_DEFAULT     = "HAYCASH SAPI DE CV"
BLOQUE_DEFAULT      = "120000"   # your original value (we output as 7 digits: zfill)


# ---------- helpers (byte-stable) ---------------------------------------
def to_fixed_300_bytes(line: str) -> bytes:
    b = line.encode("latin-1", errors="replace")
    if len(b) < 300:
        b = b + (b" " * (300 - len(b)))
    elif len(b) > 300:
        b = b[:300]
    return b


def write_fixed_file(txt_path: str, lines: list[str], final_crlf: bool = True) -> str:
    with open(txt_path, "wb") as f:
        for i, s in enumerate(lines):
            f.write(to_fixed_300_bytes(s))
            if i < len(lines) - 1 or final_crlf:
                f.write(b"\r\n")
    return txt_path


def only_digits(s: str) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def n_width_digits(s: str, width: int) -> str:
    """
    Keep ONLY digits. Left-pad with zeros to width. If longer, keep last `width` digits.
    """
    d = only_digits(s)
    if len(d) > width:
        d = d[-width:]
    return d.zfill(width)


# ---------- core generator (keeps your structure) -----------------------
class BBVAFixedGenerator:
    @staticmethod
    def header(fecha: str, bloque: str = BLOQUE_DEFAULT) -> str:
        # BBVA requires 7 chars for block; keep your value but left-pad with zeros
        bloque_7 = n_width_digits(bloque, 7)

        razon_40 = BUSINESS_EMISOR_STR.upper()[:40].ljust(40)
        rfc_18   = RFC_EMISOR_DEFAULT.upper()[:18].ljust(18)

        # Build header deterministically (byte clamp happens on write)
        parts = [
            "01",
            f"{1:07d}",          # sequence
            "30",                # op code
            "012",               # bank participant
            "E",                 # direction
            "2",                 # service
            bloque_7,            # block (7)
            fecha,               # date
            "01",                # currency
            "00",                # reject cause
            " " * 25,            # filler
            razon_40,            # business/razon social (40)
            rfc_18,              # RFC (18)
            " " * 182            # filler to 300
        ]
        return "".join(parts)

    @staticmethod
    def detail(seq: int, fecha: str, importe: float, ref_num: int,
               cliente_id: str, nombre_cliente: str, referencia: str,
               titular_servicio: str = TITULAR_DEFAULT) -> str:
        amount_cents = int(round(importe * 100))
        iva_cents    = int(round(importe * 0.16 * 100))

        # YOUR ORIGINAL INTENT, BUT SAFER:
        # - accept anything, extract digits, pad to 20
        # - (avoids crashes on non-numeric values)
        cli_20 = n_width_digits(cliente_id, 20)
        ref_7  = n_width_digits(ref_num, 7)

        nom_40 = nombre_cliente.upper()[:40].ljust(40)
        ref_40 = referencia.upper()[:40].ljust(40)
        tit_40 = titular_servicio.upper()[:40].ljust(40)
        legend = referencia.upper()[:40].ljust(40)   # ONLY reference text

        parts = [
            "02",
            f"{seq:07d}",
            "30",
            "01",
            f"{amount_cents:015d}",
            fecha,
            " " * 24,
            "51",
            fecha,
            "012",
            "01",
            cli_20,
            nom_40,
            ref_40,
            tit_40,
            f"{iva_cents:015d}",
            ref_7,
            legend,
            "00",
            " " * 21
        ]
        return ''.join(parts)

    @staticmethod
    def summary(last_detail_seq: int, num_regs: int, total_importe_cents: int, bloque: str = BLOQUE_DEFAULT) -> str:
        bloque_7 = n_width_digits(bloque, 7)
        parts = [
            "09",
            f"{last_detail_seq+1:07d}",
            "30",
            bloque_7,
            f"{num_regs:07d}",
            f"{total_importe_cents:018d}",
            " " * 257
        ]
        return "".join(parts)


# ---------- high-level API (dynamic) ------------------------------------
def generate_bbva_file(excel_path, txt_path, fecha: str, start_ref=1204000, bloque: str = BLOQUE_DEFAULT):
    # use TODAY if date box left empty
    if not fecha or fecha.strip() == "":
        fecha = datetime.now().strftime("%Y%m%d")

    ext = Path(excel_path).suffix.lower()
    df = (pd.read_excel(excel_path, dtype=str) if ext in (".xls", ".xlsx", ".xlsm")
          else pd.read_csv(excel_path, dtype=str))
    df = df.fillna("")

    lines = [BBVAFixedGenerator.header(fecha, bloque=bloque)]

    total_importe_cents = 0
    ref_counter = int(start_ref)

    for idx, row in df.iterrows():
        # EXACTLY like your original: use .get with defaults and never require column names.
        importe = float(str(row.get("Importe", "0")).replace(",", "") or "0")
        amount_cents = int(round(importe * 100))
        total_importe_cents += amount_cents

        line = BBVAFixedGenerator.detail(
            seq=idx + 2,
            fecha=fecha,
            importe=importe,
            ref_num=ref_counter,
            cliente_id=str(row.get("ID Cliente", "165197597")),  # same default you had
            nombre_cliente=str(row.get("Nombre del cliente", "")),
            referencia=str(row.get("Referencia", "")),
            titular_servicio=str(row.get("Titular del servicio", TITULAR_DEFAULT)) or TITULAR_DEFAULT
        )
        lines.append(line)
        ref_counter += 1

    last_seq = len(df) + 1
    lines.append(BBVAFixedGenerator.summary(
        last_detail_seq=last_seq,
        num_regs=len(df),
        total_importe_cents=total_importe_cents,
        bloque=bloque
    ))

    return write_fixed_file(txt_path, lines, final_crlf=True)


# ---------- GUI ----------------------------------------------------------
def main_gui():
    root = tk.Tk()
    root.title("BBVA Domiciliación – FIXED layout (300 bytes)")
    root.geometry("560x320")

    src_var, dst_var = tk.StringVar(), tk.StringVar()
    fecha_var = tk.StringVar(value="")          # empty = today
    ref_var = tk.StringVar(value="1204000")

    # display-only (client should not edit these)
    bloque_var = tk.StringVar(value=BLOQUE_DEFAULT)
    rfc_var    = tk.StringVar(value=RFC_EMISOR_DEFAULT)
    razon_var  = tk.StringVar(value=BUSINESS_EMISOR_STR)

    def pick_input():
        f = filedialog.askopenfilename(
            title="Excel con datos",
            filetypes=[("Excel", "*.xlsx *.xls *.xlsm"), ("CSV", "*.csv")]
        )
        if f:
            src_var.set(f)
            if not dst_var.get():
                dst_var.set(str(Path(f).with_suffix("")) + "_BBVA_FIXED.txt")

    def pick_output():
        f = filedialog.asksaveasfilename(
            title="Guardar TXT",
            defaultextension=".txt",
            filetypes=[("TXT", "*.txt")]
        )
        if f:
            dst_var.set(f)

    def run():
        if not src_var.get():
            messagebox.showerror("Error", "Selecciona el Excel/CSV de entrada.")
            return
        if not dst_var.get():
            messagebox.showerror("Error", "Selecciona el destino TXT.")
            return
        try:
            out = generate_bbva_file(
                src_var.get(),
                dst_var.get(),
                fecha_var.get(),
                int(ref_var.get()),
                bloque_var.get()
            )
            messagebox.showinfo("Listo", f"Archivo generado:\n{out}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    pad = {"padx": 10, "pady": 5}
    ttk.Label(root, text="BBVA Domiciliación – FIXED (300 bytes)", font=("Arial", 14, "bold")).pack(**pad)

    ttk.Label(root, text="Excel/CSV entrada:").pack(anchor="w", **pad)
    f1 = ttk.Frame(root); f1.pack(fill="x", **pad)
    ttk.Entry(f1, textvariable=src_var, width=62).pack(side="left", padx=(0, 5))
    ttk.Button(f1, text="...", width=3, command=pick_input).pack(side="left")

    ttk.Label(root, text="TXT salida:").pack(anchor="w", **pad)
    f2 = ttk.Frame(root); f2.pack(fill="x", **pad)
    ttk.Entry(f2, textvariable=dst_var, width=62).pack(side="left", padx=(0, 5))
    ttk.Button(f2, text="...", width=3, command=pick_output).pack(side="left")

    cfg = ttk.Frame(root); cfg.pack(fill="x", **pad)

    ttk.Label(cfg, text="Fecha (AAAAMMDD):").grid(row=0, column=0, sticky="w")
    ttk.Entry(cfg, textvariable=fecha_var, width=12).grid(row=0, column=1, padx=6, sticky="w")

    ttk.Label(cfg, text="Ref inicial:").grid(row=0, column=2, sticky="w", padx=(18, 6))
    ttk.Entry(cfg, textvariable=ref_var, width=12).grid(row=0, column=3, sticky="w")

    # read-only info (still shown, not editable)
    ttk.Label(cfg, text="Bloque:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(cfg, textvariable=bloque_var, width=12, state="readonly").grid(row=1, column=1, padx=6, pady=(8, 0), sticky="w")

    ttk.Label(cfg, text="RFC emisor:").grid(row=1, column=2, sticky="w", padx=(18, 6), pady=(8, 0))
    ttk.Entry(cfg, textvariable=rfc_var, width=18, state="readonly").grid(row=1, column=3, pady=(8, 0), sticky="w")

    ttk.Label(cfg, text="Razón social:").grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(cfg, textvariable=razon_var, width=48, state="readonly").grid(row=2, column=1, columnspan=3, padx=6, pady=(8, 0), sticky="w")

    ttk.Button(root, text="Generar TXT", command=run).pack(pady=18)
    root.mainloop()


if __name__ == "__main__":
    try:
        import pandas as pd  # noqa
    except ImportError:
        print("Instala:  pip install pandas openpyxl")
        sys.exit(1)
    main_gui()
