# HayCash signature wrapper (Glass + moving water) + nav sidebar + app controls in main
import os
import runpy
import base64
from pathlib import Path

import streamlit as st
import streamlit as _stmod  # monkeypatch st.sidebar output for app controls

from simple_auth import require_shared_password

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Keep a reference to the REAL sidebar before monkeypatching
_REAL_SIDEBAR = st.sidebar


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _inject_signature_css(logo_b64: str | None):
    # Use <img> in header, but keep a fallback class just in case
    logo_css = ""
    if logo_b64:
        logo_css = f"""
        .hc-logo-img {{
          height: 68px;
          width: auto;
          display: block;
          filter: drop-shadow(0 10px 18px rgba(0,0,0,0.18));
        }}
        """

    st.markdown(
        f"""
        <style>
          :root {{
            --hc-blue: #314270;
            --hc-yellow: #FFBA00;
            --glass: rgba(255, 255, 255, 0.10);
            --glass-strong: rgba(255, 255, 255, 0.16);
            --stroke: rgba(255, 255, 255, 0.22);
            --shadow: 0 18px 45px rgba(0,0,0,0.18);
          }}

          /* ===== Page layout ===== */
          .block-container {{
            max-width: 1240px;          /* consistent "same size" feel */
            padding-top: 1.25rem;
            padding-bottom: 3rem;
          }}

          /* ===== Hide Streamlit built-in multipage nav so you don't get duplicates ===== */
          nav[data-testid="stSidebarNav"],
          div[data-testid="stSidebarNav"],
          div[data-testid="stSidebarNavItems"],
          ul[data-testid="stSidebarNavItems"] {{
            display: none !important;
            height: 0 !important;
            overflow: hidden !important;
          }}

          /* ===== Hide sidebar toggle everywhere (never show in main UI) ===== */
          div[data-testid="collapsedControl"],
          div[data-testid="stSidebarCollapsedControl"],
          button[aria-label="Open sidebar"],
          button[aria-label="Close sidebar"],
          button[data-testid="stSidebarCollapseButton"],
          button[data-testid="stSidebarExpandButton"] {{
            display: none !important;
          }}

          /* ===== Animated "moving water" background (no assets needed) ===== */
          .stApp {{
            background:
              radial-gradient(1200px 600px at 10% 10%, rgba(49,66,112,0.22), transparent 60%),
              radial-gradient(900px 500px at 80% 20%, rgba(255,186,0,0.12), transparent 65%),
              radial-gradient(1000px 700px at 30% 90%, rgba(49,66,112,0.18), transparent 60%),
              linear-gradient(120deg, rgba(10,15,25,0.95), rgba(12,18,30,0.92));
            background-attachment: fixed;
            position: relative;
            overflow-x: hidden;
          }}

          /* animated water layer */
          .stApp:before {{
            content: "";
            position: fixed;
            inset: -40%;
            z-index: 0;
            background:
              radial-gradient(circle at 20% 30%, rgba(255,255,255,0.10), transparent 35%),
              radial-gradient(circle at 70% 60%, rgba(255,255,255,0.08), transparent 38%),
              radial-gradient(circle at 40% 80%, rgba(255,255,255,0.07), transparent 40%),
              radial-gradient(circle at 85% 25%, rgba(255,255,255,0.06), transparent 42%);
            filter: blur(24px);
            opacity: 0.65;
            animation: hc-water 16s ease-in-out infinite alternate;
            transform: translate3d(0,0,0);
          }}

          @keyframes hc-water {{
            0%   {{ transform: translate(-3%, -2%) scale(1.02) rotate(0.2deg); }}
            50%  {{ transform: translate(2%,  1%) scale(1.05) rotate(-0.2deg); }}
            100% {{ transform: translate(4%, -1%) scale(1.03) rotate(0.25deg); }}
          }}

          /* keep your content above background layers */
          .block-container, section[data-testid="stSidebar"] {{
            position: relative;
            z-index: 1;
          }}

          /* ===== Sidebar: glass + always looks "product" ===== */
          section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.05)) !important;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border-right: 1px solid rgba(255,255,255,0.10);
          }}
          section[data-testid="stSidebar"] .block-container {{
            padding-top: 1.15rem;
            padding-bottom: 1.25rem;
          }}

          /* ===== Header: single unified glass bar ===== */
          .hc-topbar {{
            width: 100%;
            border-radius: 18px;
            padding: 18px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;

            background: linear-gradient(135deg,
              rgba(49,66,112,0.60),
              rgba(49,66,112,0.42)
            );
            border: 1px solid rgba(255,255,255,0.18);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: var(--shadow);
          }}

          .hc-topbar-left {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 0;
            flex: 1 1 auto;
          }}

          .hc-topbar-title {{
            margin: 0;
            font-size: 1.85rem;     /* bigger presence */
            font-weight: 900;
            color: #ffffff;
            line-height: 1.12;
            letter-spacing: 0.2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }}

          .hc-topbar-subtitle {{
            margin: 0;
            font-size: 1.02rem;
            color: rgba(255,255,255,0.88);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }}

          {logo_css}

          /* Yellow accent line */
          .hc-accent {{
            height: 4px;
            width: 100%;
            border-radius: 999px;
            background: var(--hc-yellow);
            margin: 12px 0 18px 0;
            box-shadow: 0 8px 18px rgba(255,186,0,0.20);
          }}

          /* ===== Main app "frame": makes every app same shape/size visually ===== */
          .hc-frame-title {{
            margin: 0 0 10px 0;
            color: rgba(255,255,255,0.92);
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: 0.2px;
          }}

          /* Style Streamlit border containers as glass cards */
          div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 20px !important;
            border: 1px solid rgba(255,255,255,0.16) !important;
            background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.10)) !important;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 18px 45px rgba(0,0,0,0.16);
          }}

          /* Controls sizing / consistent feel */
          .stButton > button {{
            border-radius: 14px !important;
            height: 44px !important;
            padding: 0 16px !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            background: rgba(255,255,255,0.10) !important;
            color: rgba(255,255,255,0.92) !important;
          }}
          .stButton > button:hover {{
            border-color: rgba(255,186,0,0.55) !important;
            box-shadow: 0 10px 22px rgba(0,0,0,0.18);
          }}

          /* Text inputs */
          .stTextInput input, .stTextArea textarea, .stNumberInput input {{
            border-radius: 14px !important;
            background: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            color: rgba(255,255,255,0.92) !important;
          }}

          /* Dataframes keep readable on glass */
          .stDataFrame, .stDataEditor {{
            background: rgba(255,255,255,0.92) !important;
            border-radius: 14px !important;
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
    # ALWAYS render nav/title in the real sidebar (not affected by monkeypatch)
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


def _signature_header(title: str, subtitle: str, logo_b64: str | None):
    logo_html = ""
    if logo_b64:
        # REAL big logo INSIDE the same bar
        logo_html = f'<img class="hc-logo-img" src="data:image/jpg;base64,{logo_b64}" alt="HayCash" />'

    st.markdown(
        f"""
        <div class="hc-topbar">
          <div class="hc-topbar-left">
            <div class="hc-topbar-title">{title}</div>
            <div class="hc-topbar-subtitle">{subtitle}</div>
          </div>
          {logo_html}
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
    logo_b64=logo_b64,
)

# -----------------------------
# Main "frame" container: forces consistent look/size across apps
# -----------------------------
st.markdown('<div class="hc-frame-title">Aplicación</div>', unsafe_allow_html=True)

_controls_container = st.container(border=True)

# IMPORTANT: Monkeypatch AFTER sidebar nav is built (so nav stays)
_stmod.sidebar = _controls_container

# -----------------------------
# Launch original app (no logic changes)
# -----------------------------
APP_DIR = ROOT / "apps" / "cdf_isaac"
os.chdir(APP_DIR)
runpy.run_path(str(APP_DIR / "app_isaac.py"), run_name="__main__")
