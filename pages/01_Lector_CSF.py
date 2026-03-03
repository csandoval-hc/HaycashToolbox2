# pages/01_Lector_CSF.py
# HayCash signature wrapper: consistent look + nav-only sidebar
import os
import runpy
import base64
from pathlib import Path

import streamlit as st
import streamlit as _stmod  # monkeypatch target

from simple_auth import require_shared_password

# --- Robust ROOT detection (fixes /apps/apps/...) ---
_THIS = Path(__file__).resolve()
ROOT = None
for p in [_THIS] + list(_THIS.parents):
    if (p / "app.py").exists():  # main toolbox entrypoint
        ROOT = p
        break
if ROOT is None:
    ROOT = _THIS.parents[1]

SAFE_ROOT = ROOT
ASSETS = ROOT / "assets"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _inject_signature_css(logo_b64: str | None):
    logo_css = ""
    if logo_b64:
        logo_css = f"""
        .hc-topbar-logo {{
          background-image: url("data:image/jpg;base64,{logo_b64}");
          background-repeat: no-repeat;
          background-position: right center;
          background-size: contain;
          width: 600px;
          height: 140px;
          flex-shrink: 0;
        }}
        """

    st.markdown(
        f"""
        <style>
          header[data-testid="stHeader"] {{
            height: 0 !important;
            min-height: 0 !important;
            display: none !important;
          }}

          .block-container {{
            padding-top: 3.25rem !important;
            padding-bottom: 2rem !important;
            max-width: 98% !important;
          }}

          [data-testid="stSidebarNav"] {{ display: none !important; }}

          section[data-testid="stSidebar"] {{
            background-color: #f8f9fa;
            border-right: 1px solid #e0e0e0;
          }}

          .hc-topbar {{
            width: 100%;
            background: #314270;
            border-radius: 12px 12px 0 0;
            padding: 15px 25px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 160px;
          }}

          .hc-topbar-title {{
            margin: 0;
            font-size: 1.8rem;
            font-weight: 800;
            color: #ffffff;
          }}

          .hc-topbar-subtitle {{
            margin: 0;
            font-size: 1rem;
            color: rgba(255,255,255,0.85);
          }}

          {logo_css}

          .hc-accent {{
            height: 5px;
            width: 100%;
            background: #FFBA00;
            border-radius: 0 0 12px 12px;
            margin-bottom: 2rem;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_nav():
    with st.sidebar:
        logo = ASSETS / "haycash_logo.jpg"
        if logo.exists():
            st.image(str(logo), use_container_width=True)

        st.markdown("### HayCash ToolBox")
        st.caption("NAVEGACIÓN PRINCIPAL")
        st.divider()

        st.page_link("app.py", label="🏠 Inicio")
        st.page_link("pages/01_Lector_CSF.py", label="🧾 Lector CSF")
        st.page_link("pages/02_CSV_a_TXT_BBVA.py", label="🏦 CSV a TXT BBVA")
        st.page_link("pages/03_Reporte_Interactivo_de_Leads.py", label="📊 Reporte Leads")
        st.page_link("pages/04_Factoraje.py", label="💳 Factoraje")
        st.page_link("pages/05_Lector_edocat.py", label="📄 Lector Edocat")
        st.page_link("pages/06_reporte_consejo.py", label="📈 Reporte Consejo")
        st.page_link("pages/07_lector_contrato.py", label="📝 Lector Contrato")

        st.divider()
        if st.session_state.get("auth_ok"):
            user = st.session_state.get("auth_user") or "-"
            st.caption(f"Usuario: **{user}**")


def _signature_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="hc-topbar">
          <div>
            <div class="hc-topbar-title">{title}</div>
            <div class="hc-topbar-subtitle">{subtitle}</div>
          </div>
          <div class="hc-topbar-logo"></div>
        </div>
        <div class="hc-accent"></div>
        """,
        unsafe_allow_html=True,
    )


def _looks_like_csf_app(py_path: Path) -> bool:
    """
    Heuristic: your CSF app has strong signatures (pdfplumber/pytesseract/pdf2image, CSF strings, etc.)
    We use this to auto-find the entrypoint even if it was renamed/moved.
    """
    try:
        txt = py_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # Avoid running wrappers/pages
    if "/pages/" in str(py_path).replace("\\", "/"):
        return False

    needles = [
        "pdfplumber",
        "pytesseract",
        "pdf2image",
        "convert_from_path",
        "CONSTANCIA",
        "SITUACIÓN FISCAL",
        "SITUACION FISCAL",
        "parse_csf_fields",
        "Generar Excel desde CSF/CFDI",
    ]
    score = sum(1 for n in needles if n in txt)
    return score >= 3  # tuned for your posted CSF script


def _find_csf_entrypoint() -> Path | None:
    # 1) Try the most likely locations first
    preferred = [
        ROOT / "apps" / "lector_csf" / "streamlit_app.py",
        ROOT / "apps" / "lector_csf" / "app.py",
        ROOT / "apps" / "lector_csf" / "CDF_isaac.py",
        ROOT / "apps" / "lector_csf" / "cdf_isaac.py",
        ROOT / "apps" / "cdf_isaac" / "streamlit_app.py",
        ROOT / "apps" / "cdf_isaac" / "app.py",
        ROOT / "apps" / "cdf_isaac" / "CDF_isaac.py",
        ROOT / "apps" / "cdf_isaac" / "cdf_isaac.py",
    ]
    for p in preferred:
        if p.exists():
            return p

    # 2) If renamed/moved: scan under ROOT/apps then whole ROOT
    scan_roots = [ROOT / "apps", ROOT]
    seen = set()
    candidates: list[Path] = []
    for base in scan_roots:
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            py_str = str(py.resolve())
            if py_str in seen:
                continue
            seen.add(py_str)
            if py.name.startswith("_"):
                continue
            if py.name == "app.py" and "/pages/" in py_str.replace("\\", "/"):
                continue
            if _looks_like_csf_app(py):
                candidates.append(py)

    # Prefer something inside /apps/
    candidates.sort(key=lambda p: (0 if "/apps/" in str(p).replace("\\", "/") else 1, len(str(p))))
    return candidates[0] if candidates else None


# --- PAGE SETUP ---
st.set_page_config(page_title="HayCash ToolBox", layout="wide", initial_sidebar_state="expanded")

require_shared_password()

logo_file = ASSETS / "haycash_logo.jpg"
logo_b64 = _b64(logo_file) if logo_file.exists() else None
_inject_signature_css(logo_b64)

_sidebar_nav()

_signature_header(
    title="Lector CSF",
    subtitle="Procesamiento y validación de Constancias de Situación Fiscal.",
)

with st.container(border=True):
    control_space = st.container()

_ORIGINAL_SIDEBAR = _stmod.sidebar
_ORIGINAL_CWD = os.getcwd()

try:
    _stmod.sidebar = control_space

    entrypoint = _find_csf_entrypoint()
    if entrypoint is None:
        # Show debugging info to fix fast
        st.error("No pude encontrar el entrypoint del Lector CSF automáticamente.")
        st.write("Revisa que exista un .py del CSF dentro de /apps/ (o en el repo).")
        st.write("ROOT detectado:", str(ROOT))
        st.write("Contenido de ROOT/apps:")
        apps_dir = ROOT / "apps"
        if apps_dir.exists():
            st.write([p.name for p in apps_dir.iterdir()])
        st.stop()

    # Embedded flags
    os.environ["HC_EMBEDDED"] = "1"
    os.environ["HC_SKIP_PAGE_CONFIG"] = "1"
    os.environ["HC_SKIP_INTERNAL_AUTH"] = "1"

    os.chdir(entrypoint.parent)
    runpy.run_path(str(entrypoint), run_name="__main__")

except Exception as e:
    st.error(f"Application Error: {e}")
    st.exception(e)

finally:
    _stmod.sidebar = _ORIGINAL_SIDEBAR
    try:
        os.chdir(_ORIGINAL_CWD)
    except Exception:
        os.chdir(SAFE_ROOT)

    for k in ["HC_EMBEDDED", "HC_SKIP_PAGE_CONFIG", "HC_SKIP_INTERNAL_AUTH"]:
        os.environ.pop(k, None)
