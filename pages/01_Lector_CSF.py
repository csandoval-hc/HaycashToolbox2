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
          width: 190px;
          height: 44px;
          flex: 0 0 190px;
        }}
        """

    st.markdown(
        f"""
        <style>
          /* Consistent page width and spacing */
          .block-container {{
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
            max-width: 1180px;
          }}

          /* Hide Streamlit built-in multipage navigation (prevents duplicate menu) */
          nav[data-testid="stSidebarNav"],
          div[data-testid="stSidebarNav"],
          div[data-testid="stSidebarNavItems"],
          ul[data-testid="stSidebarNavItems"] {{
            display: none !important;
            height: 0 !important;
            overflow: hidden !important;
          }}

          /* Hide sidebar toggle controls so they never appear in main UI */
          div[data-testid="collapsedControl"],
          div[data-testid="stSidebarCollapsedControl"],
          button[aria-label="Open sidebar"],
          button[aria-label="Close sidebar"],
          button[data-testid="stSidebarCollapseButton"],
          button[data-testid="stSidebarExpandButton"] {{
            display: none !important;
          }}

          /* Sidebar look */
          section[data-testid="stSidebar"] {{
            border-right: 1px solid rgba(17, 24, 39, 0.08);
          }}
          section[data-testid="stSidebar"] .block-container {{
            padding-top: 1.25rem;
          }}

          /* ===== Header: ONE unified blue bar (logo inside the same bar) ===== */
          .hc-topbar {{
            width: 100%;
            background: #314270;
            border-radius: 14px;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
          }}
          .hc-topbar-left {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            min-width: 0;
          }}
          .hc-topbar-title {{
            margin: 0;
            font-size: 1.45rem;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.15;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }}
          .hc-topbar-subtitle {{
            margin: 0;
            font-size: 0.95rem;
            color: rgba(255,255,255,0.85);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }}
          {logo_css}

          /* Accent line: yellow */
          .hc-accent {{
            height: 4px;
            width: 100%;
            border-radius: 999px;
            background: #FFBA00;
            margin: 10px 0 18px 0;
          }}

          /* Professional buttons/inputs */
          .stButton > button {{
            border-radius: 12px;
            height: 42px;
            padding: 0 14px;
            border: 1px solid rgba(49, 66, 112, 0.20);
          }}
          .stTextInput input, .stSelectbox div, .stTextArea textarea, .stNumberInput input {{
            border-radius: 12px;
          }}

          /* st.container(border=True) cards */
          div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 18px;
            border: 1px solid rgba(17, 24, 39, 0.08);
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
    # Sidebar should still have navigation + title presence
    with st.sidebar:
        logo = ASSETS / "haycash_logo.jpg"
        if logo.exists():
            st.image(str(logo), use_container_width=True)

        st.markdown("## HayCash ToolBox")
        st.caption("Navegación")
        st.divider()

        _safe_page_link("app.py", "🧰 Inicio")
        _safe_page_link("pages/01_Lector_CSF.py", "🧾 Lector CSF")
        _safe_page_link("pages/02_CSV_a_TXT_BBVA.py", "🏦 CSV a TXT BBVA")
        _safe_page_link("pages/03_Reporte_Interactivo_de_Leads.py", "📊 Reporte Interactivo de Leads")
        _safe_page_link("pages/04_Factoraje.py", "💳 Factoraje")
        _safe_page_link("pages/05_Lector_edocat.py", "📄 Lector Edocat")
        _safe_page_link("pages/06_reporte_consejo.py", "📈 Reporte Consejo")
        _safe_page_link("pages/07_lector_contrato.py", "📝 Lector Contrato")

        st.divider()
        if st.session_state.get("auth_ok"):
            user = st.session_state.get("auth_user") or "-"
            st.caption(f"Sesión: **{user}**")


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
# KEY FIX: Move app controls out of sidebar into main page (UI-only)
# DO NOT add wrapper headings like "Entradas" to avoid duplicates.
# -----------------------------
_controls_container = st.container(border=True)
_stmod.sidebar = _controls_container

# -----------------------------
# Launch original app (no logic changes)
# -----------------------------
APP_DIR = ROOT / "apps" / "cdf_isaac"
os.chdir(APP_DIR)
runpy.run_path(str(APP_DIR / "app_isaac.py"), run_name="__main__")
