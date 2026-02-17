# HayCash signature wrapper: consistent look + nav-only sidebar
import os
import runpy
from pathlib import Path

import streamlit as st
import streamlit as _stmod  # used for monkeypatching sidebar output

from simple_auth import require_shared_password

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def _inject_signature_css():
    st.markdown(
        """
        <style>
          /* Consistent page width and spacing */
          .block-container {
            padding-top: 1.75rem;
            padding-bottom: 2.5rem;
            max-width: 1180px;
          }

          /* Hide Streamlit built-in multipage navigation (prevents duplicate menu)
             Different Streamlit builds use different DOM shapes, so we hide multiple. */
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
            padding-top: 1.25rem;
          }

          /* Header card */
          .hc-header {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 16px;
            border: 1px solid rgba(17, 24, 39, 0.08);
            border-radius: 18px;
            background: #ffffff;
            box-shadow: 0 10px 25px rgba(0,0,0,0.06);
          }
          .hc-title {
            margin: 0;
            font-size: 1.55rem;
            line-height: 1.2;
            font-weight: 700;
            color: #111827;
          }
          .hc-subtitle {
            margin: 4px 0 0 0;
            opacity: 0.8;
            color: #111827;
          }

          /* Accent line: BLUE ONLY (per your request) */
          .hc-accent {
            height: 4px;
            width: 100%;
            border-radius: 999px;
            background: #314270;
            margin: 14px 0 18px 0;
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


def _safe_page_link(path: str, label: str):
    try:
        st.page_link(path, label=label)
    except Exception:
        # don't crash if a page is missing
        st.caption(label)


def _sidebar_nav():
    # Sidebar must be NAVIGATION ONLY
    with st.sidebar:
        logo = ASSETS / "haycash_logo.jpg"
        if logo.exists():
            st.image(str(logo), use_container_width=True)

        st.markdown("### HayCash ToolBox")
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
        <div class="hc-header">
          <div>
            <div class="hc-title">{title}</div>
            <div class="hc-subtitle">{subtitle}</div>
          </div>
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

_inject_signature_css()
_sidebar_nav()
_signature_header(
    title="Lector CSF",
    subtitle="Generar Excel desde CSF/CFDI (SAT).",
)

# -----------------------------
# KEY FIX: Move sidebar controls into main page (UI-only)
# The original app uses st.sidebar.<widgets>.
# We redirect st.sidebar to a main-page container so controls render in main.
# -----------------------------
st.subheader("Entradas")
_controls_container = st.container(border=True)

# Monkeypatch streamlit module's sidebar target
_stmod.sidebar = _controls_container  # redirects st.sidebar.* calls to main page container

# -----------------------------
# Launch original app (no logic changes)
# -----------------------------
APP_DIR = ROOT / "apps" / "cdf_isaac"
os.chdir(APP_DIR)
runpy.run_path(str(APP_DIR / "app_isaac.py"), run_name="__main__")
