# HayCash signature wrapper: consistent look + nav-only sidebar
import os
import runpy
import base64
from pathlib import Path

import streamlit as st
import streamlit as _stmod  # monkeypatch st.sidebar output for app controls

from simple_auth import require_shared_password

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# IMPORTANT: keep a reference to the real sidebar before monkeypatching
_REAL_SIDEBAR = st.sidebar


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _inject_signature_css(logo_b64: str | None):
    logo_css = ""
    if logo_b64:
        # Bigger logo, better fit
        logo_css = f"""
        .hc-topbar-logo {{
          background-image: url("data:image/jpg;base64,{logo_b64}");
          background-repeat: no-repeat;
          background-position: right center;
          background-size: contain;
          width: 200px;       /* Adjusted for better scaling */
          height: 80px;       
          flex-shrink: 0;     /* Prevent logo from shrinking */
        }}
        """

    st.markdown(
        f"""
        <style>
          /* Consistent page width and spacing */
          .block-container {{
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 95%;     /* Use percentage to avoid cutoff on smaller screens */
          }}

          /* Hide ONLY the default Streamlit nav, but keep sidebar visible */
          [data-testid="stSidebarNav"] {{
            display: none !important;
          }}

          /* Sidebar styling */
          section[data-testid="stSidebar"] {{
            background-color: #f8f9fa;
            border-right: 1px solid rgba(17, 24, 39, 0.08);
            min-width: 300px !important;
          }}

          /* ===== Header: ONE unified blue bar ===== */
          .hc-topbar {{
            width: 100%;
            background: #314270;
            border-radius: 14px;
            padding: 20px 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
          }}
          .hc-topbar-left {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            overflow: hidden;
          }}
          .hc-topbar-title {{
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
          }}
          .hc-topbar-subtitle {{
            margin: 0;
            font-size: 1.1rem;
            color: rgba(255,255,255,0.9);
          }}
          {logo_css}

          /* Accent line: yellow */
          .hc-accent {{
            height: 5px;
            width: 98%;
            margin: -5px auto 25px auto;
            border-radius: 0 0 10px 10px;
            background: #FFBA00;
            z-index: 10;
          }}

          /* Professional buttons/inputs */
          .stButton > button {{
            border-radius: 10px;
            font-weight: 600;
          }}
          
          /* Fix for container borders */
          div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 18px !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_page_link(path: str, label: str):
    try:
        st.page_link(path, label=label)
    except Exception:
        st.caption(label)


def _sidebar_nav():
    # Write directly to the real sidebar
    with _REAL_SIDEBAR:
        logo = ASSETS / "haycash_logo.jpg"
        if logo.exists():
            st.image(str(logo), use_container_width=True)

        st.markdown("### HayCash ToolBox")
        st.caption("NAVEGACIÓN PRINCIPAL")
        st.divider()

        _safe_page_link("app.py", "🏠 Inicio")
        _safe_page_link("pages/01_Lector_CSF.py", "🧾 Lector CSF")
        _safe_page_link("pages/02_CSV_a_TXT_BBVA.py", "🏦 CSV a TXT BBVA")
        _safe_page_link("pages/03_Reporte_Interactivo_de_Leads.py", "📊 Reporte Leads")
        _safe_page_link("pages/04_Factoraje.py", "💳 Factoraje")
        _safe_page_link("pages/05_Lector_edocat.py", "📄 Lector Edocat")
        _safe_page_link("pages/06_reporte_consejo.py", "📈 Reporte Consejo")
        _safe_page_link("pages/07_lector_contrato.py", "📝 Lector Contrato")

        st.divider()
        if st.session_state.get("auth_ok"):
            user = st.session_state.get("auth_user") or "-"
            st.info(f"Usuario: **{user}**")


def _signature_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="hc-topbar">
          <div class="hc-topbar-left">
            <div class="hc-topbar-title">{title}</div>
            <div class="hc-topbar-subtitle">{subtitle}</div>
          </div>
          <div class="hc-topbar-logo"></div>
        </div>
        <div class="hc-accent"></div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="HayCash ToolBox", layout="wide", initial_sidebar_state="expanded")
require_shared_password()

logo_file = ASSETS / "haycash_logo.jpg"
logo_b64 = _b64(logo_file) if logo_file.exists() else None

_inject_signature_css(logo_b64)
_sidebar_nav()
_signature_header(
    title="Lector CSF",
    subtitle="Generar Excel desde CSF/CFDI (SAT).",
)

# -----------------------------
# KEY FIX: Redirect sidebar calls to a container in the main body
# -----------------------------
_controls_container = st.container(border=True)
_stmod.sidebar = _controls_container

# -----------------------------
# Launch original app
# -----------------------------
APP_DIR = ROOT / "apps" / "cdf_isaac"
os.chdir(APP_DIR)
runpy.run_path(str(APP_DIR / "app_isaac.py"), run_name="__main__")
