# HayCash signature wrapper: consistent look + nav-only sidebar + app controls in main
import os
import runpy
from pathlib import Path

import streamlit as st
import streamlit as _stmod  # monkeypatch st.sidebar output for app controls

from simple_auth import require_shared_password

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Keep a handle to the REAL sidebar before monkeypatching
_REAL_SIDEBAR = st.sidebar


def _inject_signature_css():
    st.markdown(
        """
        <style>
          /* Make the main content use the full width so header never clips */
          .block-container {
            padding-top: 1.0rem;
            padding-bottom: 2.5rem;
            max-width: 1400px;
          }

          /* Hide Streamlit built-in multipage navigation (prevents duplicate menu) */
          nav[data-testid="stSidebarNav"],
          div[data-testid="stSidebarNav"],
          div[data-testid="stSidebarNavItems"],
          ul[data-testid="stSidebarNavItems"] {
            display: none !important;
            height: 0 !important;
            overflow: hidden !important;
          }

          /* Hide sidebar toggle controls so they never appear in main UI */
          div[data-testid="collapsedControl"],
          div[data-testid="stSidebarCollapsedControl"],
          button[aria-label="Open sidebar"],
          button[aria-label="Close sidebar"],
          button[data-testid="stSidebarCollapseButton"],
          button[data-testid="stSidebarExpandButton"] {
            display: none !important;
          }

          /* Sidebar look */
          section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(17, 24, 39, 0.08);
          }
          section[data-testid="stSidebar"] .block-container {
            padding-top: 1.0rem;
          }

          /* Header bar */
          .hc-topbar {
            background: #314270;
            border-radius: 14px;
            padding: 14px 18px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
          }
          .hc-title {
            margin: 0;
            color: #fff;
            font-size: 1.55rem;
            font-weight: 900;
            line-height: 1.15;
          }
          .hc-subtitle {
            margin-top: 4px;
            color: rgba(255,255,255,0.85);
            font-size: 0.98rem;
          }

          /* Yellow accent line */
          .hc-accent {
            height: 4px;
            width: 100%;
            border-radius: 999px;
            background: #FFBA00;
            margin: 10px 0 18px 0;
          }

          /* Professional buttons/inputs */
          .stButton > button {
            border-radius: 12px;
            height: 42px;
            padding: 0 14px;
            border: 1px solid rgba(49, 66, 112, 0.20);
          }
          .stTextInput input, .stSelectbox div, .stTextArea textarea, .stNumberInput input {
            border-radius: 12px;
          }

          /* st.container(border=True) cards */
          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 18px;
            border: 1px solid rgba(17, 24, 39, 0.08);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_page_link(page: str, label: str):
    try:
        st.page_link(page, label=label)
    except Exception:
        st.caption(label)


def _render_sidebar_nav():
    # Use REAL sidebar object so it won't be affected by monkeypatch later
    with _REAL_SIDEBAR:
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


def _render_header(title: str, subtitle: str):
    # One unified bar: left text, right logo INSIDE bar, no clipping, logo sized correctly.
    logo = ASSETS / "haycash_logo.jpg"

    bar = st.container()
    with bar:
        left, right = st.columns([8, 2], vertical_alignment="center")
        with left:
            st.markdown(
                f"""
                <div class="hc-topbar">
                  <div class="hc-title">{title}</div>
                  <div class="hc-subtitle">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            # Put logo inside same visual row; match height to bar
            if logo.exists():
                st.image(str(logo), use_container_width=True)

    st.markdown("<div class='hc-accent'></div>", unsafe_allow_html=True)


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="HayCash ToolBox", layout="wide", initial_sidebar_state="expanded")
require_shared_password()

_inject_signature_css()

# Sidebar nav MUST render before monkeypatch
_render_sidebar_nav()

# Header
_render_header(
    title="Lector CSF",
    subtitle="Generar Excel desde CSF/CFDI (SAT).",
)

# -----------------------------
# Move app's st.sidebar widgets into MAIN page (UI-only)
# -----------------------------
_controls_container = st.container(border=True)

# Redirect st.sidebar.* calls for the APP ONLY (after nav is built)
_stmod.sidebar = _controls_container

# -----------------------------
# Launch original app (no logic changes)
# -----------------------------
APP_DIR = ROOT / "apps" / "cdf_isaac"
os.chdir(APP_DIR)
runpy.run_path(str(APP_DIR / "app_isaac.py"), run_name="__main__")
