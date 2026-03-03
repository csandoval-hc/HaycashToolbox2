# HayCash signature wrapper: consistent look + nav-only sidebar
import os
import runpy
import base64
from pathlib import Path

import streamlit as st
import streamlit as _stmod  # Needed for the monkeypatch

from simple_auth import require_shared_password

# --- Robust ROOT detection ---
_THIS = Path(__file__).resolve()
ROOT = None
for p in [_THIS] + list(_THIS.parents):
    if (p / "app.py").exists():
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

    APP_DIR = ROOT / "apps" / "lector_csf"
    if not APP_DIR.exists():
        raise FileNotFoundError(f"App directory not found: {APP_DIR}")

    os.environ["HC_EMBEDDED"] = "1"
    os.environ["HC_SKIP_PAGE_CONFIG"] = "1"
    os.environ["HC_SKIP_INTERNAL_AUTH"] = "1"

    os.chdir(APP_DIR)
    runpy.run_path(str(APP_DIR / "streamlit_app.py"), run_name="__main__")

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
