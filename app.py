import base64
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="HayCash ToolBox", 
    page_icon="💎", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

require_shared_password()

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

def b64(path: Path) -> str:
    if not path.exists(): return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    cfg_path = ROOT / "apps.yaml"
    if not cfg_path.exists(): return []
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
logo_b64 = b64(ASSETS / "haycash_logo.jpg")

# --- HIGH-END CSS ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

        /* 1. Ultra-Clean Professional Background */
        .stApp {{
            background: radial-gradient(circle at top right, #314270, #1a1a2e);
            font-family: 'Inter', sans-serif;
        }}

        /* 2. Fix Container and Padding */
        .block-container {{
            padding-top: 3rem !important;
            max-width: 1250px !important;
        }}

        /* 3. Hide Default Streamlit Nav & Sidebar Toggles */
        [data-testid="stSidebarNav"], 
        [data-testid="collapsedControl"],
        button[aria-label="Open sidebar"],
        button[aria-label="Close sidebar"] {{
            display: none !important;
        }}

        /* 4. Glassmorphic Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.03) !important;
            backdrop-filter: blur(15px);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }}

        /* 5. Unified Header Bar (Matches Sub-apps) */
        .hc-hero {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(10px);
        }}
        .hero-text h1 {{
            color: white;
            font-size: 3.5rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -2px;
        }}
        .hero-text p {{
            color: rgba(255,255,255,0.7);
            font-size: 1.2rem;
            margin-top: 10px;
        }}

        /* 6. Professional Tool Cards */
        .tool-card {{
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 30px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            height: 280px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .tool-card:hover {{
            background: rgba(255, 255, 255, 0.12);
            transform: translateY(-10px);
            border-color: #FFBA00;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}
        .tool-icon-circle {{
            width: 60px;
            height: 60px;
            background: rgba(255, 186, 0, 0.1);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            margin-bottom: 20px;
        }}
        .tool-name {{
            color: white;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .tool-desc {{
            color: rgba(255,255,255,0.5);
            font-size: 0.95rem;
            line-height: 1.5;
        }}

        /* 7. Action Button Styling */
        div.stButton > button {{
            background: #FFBA00 !important;
            color: #1a1a2e !important;
            border-radius: 12px !important;
            border: none !important;
            font-weight: 700 !important;
            padding: 10px 24px !important;
            width: 100%;
            transition: all 0.3s ease;
        }}
        div.stButton > button:hover {{
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(255, 186, 0, 0.4);
        }}
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAV ---
with st.sidebar:
    if logo_b64:
        st.markdown(f'<img src="data:image/jpg;base64,{logo_b64}" style="width:100%; margin-bottom:20px; border-radius:10px;">', unsafe_allow_html=True)
    
    st.markdown("<h2 style='color:white; margin-bottom:0;'>HayCash</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:rgba(255,255,255,0.5);'>Studio Management</p>", unsafe_allow_html=True)
    st.divider()
    
    # Re-rendering the links manually for the " jaw dropping" look
    for app_id, page in PAGE_BY_ID.items():
        name = next((a.get("name") for a in apps if a.get("id") == app_id), app_id.replace("_", " ").title())
        if st.sidebar.button(f" {name}", key=f"side_{app_id}", use_container_width=True):
            st.switch_page(page)

# --- MAIN HERO SECTION ---
st.markdown(f"""
    <div class="hc-hero">
        <div class="hero-text">
            <h1>ToolBox <span style="color:#FFBA00;">Pro</span></h1>
            <p>Sistemas integrados de gestión y automatización financiera.</p>
        </div>
        <img src="data:image/jpg;base64,{logo_b64}" style="height:80px; opacity:0.8;">
    </div>
""", unsafe_allow_html=True)

# --- APP GRID ---
st.markdown("<h3 style='color:white; margin-bottom:30px; font-weight:400;'>Herramientas Disponibles</h3>", unsafe_allow_html=True)

cols = st.columns(3, gap="large")
for i, a in enumerate(apps):
    with cols[i % 3]:
        # Custom Tool Card Render
        st.markdown(f"""
            <div class="tool-card">
                <div>
                    <div class="tool-icon-circle">
                        {"🧾" if "CSF" in a.get("name") else "🏦" if "BBVA" in a.get("name") else "📊" if "Leads" in a.get("name") else "💳" if "Factoraje" in a.get("name") else "📄" if "Edocat" in a.get("name") else "📈" if "Consejo" in a.get("name") else "📝"}
                    </div>
                    <div class="tool-name">{a.get("name")}</div>
                    <div class="tool-desc">Acceda al módulo de {a.get("name").lower()} para procesar datos y generar reportes.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Link logic
        if st.button("Lanzar Aplicación", key=f"main_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                st.switch_page(target)
            else:
                st.error("Ruta no configurada.")
        st.markdown("<br>", unsafe_allow_html=True)
