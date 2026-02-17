import base64
from pathlib import Path

import streamlit as st
import yaml

from simple_auth import require_shared_password

# Keep crown (Streamlit default) by not setting page_icon
st.set_page_config(page_title="HayCash ToolBox", layout="wide", initial_sidebar_state="expanded")

require_shared_password()

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def load_registry():
    cfg_path = ROOT / "apps.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return cfg.get("apps", [])


PAGE_BY_ID = {
    "cdf_isaac": "pages/01_Lector_CSF.py",
    "diegobbva": "pages/02_CSV_a_TXT_BBVA.py",
    "analisis_leads": "pages/03_Reporte_Interactivo_de_Leads.py",
    "factoraje": "pages/04_Factoraje.py",
    "lector_edocat": "pages/05_Lector_edocat.py",
    "reporte_consejo": "pages/06_reporte_consejo.py",
    "lector_contrato": "pages/07_lector_contrato.py",
}


apps = load_registry()

# Background + simple styling (keeps existing look as much as possible)
bg = ASSETS / "bg.jpg"
logo = ASSETS / "haycash_logo.jpg"

st.markdown(
    f"""
    <style>
      /* --- HARD HIDE: sidebar open/close controls everywhere --- */
      /* Floating "open sidebar" control that appears in main */
      div[data-testid="collapsedControl"] {{
        display: none !important;
      }}
      div[data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
      }}

      /* Header buttons (Open sidebar / Close sidebar) */
      button[aria-label="Open sidebar"] {{
        display: none !important;
      }}
      button[aria-label="Close sidebar"] {{
        display: none !important;
      }}

      /* Some Streamlit versions use these testids for the toggle button */
      button[data-testid="stSidebarCollapseButton"] {{
        display: none !important;
      }}
      button[data-testid="stSidebarExpandButton"] {{
        display: none !important;
      }}

      /* Ensure sidebar stays visible (best-effort) */
      section[data-testid="stSidebar"] {{
        transform: none !important;
        visibility: visible !important;
      }}

      .stApp {{
        background-image: url("data:image/jpg;base64,{b64(bg)}");
        background-size: cover;
        background-attachment: fixed;
      }}
      .block-container {{
        padding-top: 2rem;
        max-width: 1200px;
      }}
      .card {{
        background: rgba(255,255,255,0.88);
        border-radius: 16px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.10);
        height: 100%;
      }}
      .card h3 {{
        margin: 0 0 6px 0;
      }}
      .card p {{
        margin: 0;
        opacity: 0.8;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 4], vertical_alignment="center")
with col1:
    st.image(str(logo), use_container_width=True)
with col2:
    st.title("HayCash ToolBox")
    st.caption("Seleccione una herramienta")

# Grid of cards with buttons
cols = st.columns(3)
for i, a in enumerate(apps):
    with cols[i % 3]:
        icon_path = ROOT / a.get("icon", "")
        icon_html = ""
        if icon_path.exists():
            icon_html = (
                f'<img src="data:image/svg+xml;base64,{b64(icon_path)}" '
                f'style="width:38px;height:38px;margin-right:10px;" />'
            )
        st.markdown(
            f"""<div class="card">
                <div style="display:flex;align-items:center;gap:10px;">
                    {icon_html}
                    <h3>{a.get("name","")}</h3>
                </div>
              </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Abrir", key=f"open_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                st.switch_page(target)
            else:
                st.warning("Página no encontrada para esta herramienta.")
