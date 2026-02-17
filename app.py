import base64
import time
import os
import sys
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- 0. SAFETY LOCK (Crash Prevention) ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent
    if os.getcwd() != str(PROJECT_ROOT):
        os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
except Exception:
    pass

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="HayCash ToolBox",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed" 
)

require_shared_password()

ASSETS = PROJECT_ROOT / "assets"

# --- 2. HELPERS ---
def b64(path: Path) -> str:
    if not path.exists(): return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    try:
        cfg_path = PROJECT_ROOT / "apps.yaml"
        if not cfg_path.exists(): return []
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return cfg.get("apps", [])
    except Exception:
        return []

def safe_navigate(page_path, app_name):
    try:
        with st.spinner(f"Accediendo a {app_name}..."):
            time.sleep(0.2)
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)
        st.switch_page(page_path)
    except Exception as e:
        st.error(f"Error de navegación: {e}")

# --- 3. LOAD ASSETS ---
apps = load_registry()
logo_b64 = b64(ASSETS / "haycash_logo.jpg")

# --- 4. MAP ---
PAGE_BY_ID = {
    "cdf_isaac": "pages/01_Lector_CSF.py",
    "diegobbva": "pages/02_CSV_a_TXT_BBVA.py",
    "analisis_leads": "pages/03_Reporte_Interactivo_de_Leads.py",
    "factoraje": "pages/04_Factoraje.py",
    "lector_edocat": "pages/05_Lector_edocat.py",
    "reporte_consejo": "pages/06_reporte_consejo.py",
    "lector_contrato": "pages/07_lector_contrato.py",
}

# --- 5. THE "EXECUTIVE GLASS" DESIGN SYSTEM ---
st.markdown(f"""
    <style>
        /* FONT IMPORT */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* RESET & BACKGROUND */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: #050505; 
            color: #ffffff;
        }}
        
        .stApp {{
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, #020617 60%);
            background-attachment: fixed;
        }}

        /* KILL THE SIDEBAR COMPLETELY */
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"], 
        section[data-testid="stSidebar"] {{
            display: none !important;
            width: 0px !important;
        }}
        
        /* HEADER & PADDING */
        .block-container {{
            padding-top: 3rem !important;
            padding-bottom: 5rem !important;
            max-width: 1300px !important;
        }}
        header[data-testid="stHeader"] {{
            background: transparent !important;
            backdrop-filter: none !important;
        }}

        /* --- HEADER STYLES --- */
        .hc-header {{
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 25px;
            margin-bottom: 60px;
            padding-bottom: 30px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .hc-logo {{
            width: 80px;
            height: 80px;
            border-radius: 18px;
            box-shadow: 0 0 30px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .hc-title-group h1 {{
            font-size: 3rem;
            font-weight: 800;
            margin: 0;
            line-height: 1;
            background: linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }}
        
        .hc-title-group p {{
            color: #64748B;
            font-size: 1.1rem;
            margin: 8px 0 0 0;
            font-weight: 400;
        }}

        /* --- GLASS CARDS --- */
        /* This removes the Streamlit container default styling */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
        }}

        .glass-card {{
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 30px 25px;
            height: 260px;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}

        .glass-card:hover {{
            transform: translateY(-8px);
            border-color: rgba(255, 186, 0, 0.5); /* Gold border on hover */
            background: rgba(30, 41, 59, 0.7);
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }}

        .icon-circle {{
            width: 54px;
            height: 54px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.02));
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            color: #FFBA00;
        }}

        .card-title {{
            font-size: 1.3rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
        }}

        .card-sub {{
            font-size: 0.9rem;
            color: #94A3B8;
            line-height: 1.4;
        }}

        /* --- THE BUTTON (FIXED) --- */
        /* We force the Streamlit button to fill the bottom of the card area visually */
        
        .stButton {{
            width: 100%;
            margin-top: 15px;
        }}
        
        div.stButton > button {{
            width: 100%;
            background: #FFBA00 !important;
            border: none !important;
            color: #020617 !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 12px 0 !important;
            border-radius: 10px !important;
            transition: all 0.2s ease;
            box-shadow: 0 4px 15px rgba(255, 186, 0, 0.2);
        }}

        div.stButton > button:hover {{
            background: #FFFFFF !important;
            color: #000000 !important;
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(255, 255, 255, 0.3);
        }}

        div.stButton > button:active {{
            transform: scale(0.98);
        }}

    </style>
""", unsafe_allow_html=True)

# --- 6. RENDER HEADER ---
logo_html = f'<img src="data:image/jpg;base64,{logo_b64}" class="hc-logo">' if logo_b64 else ""

st.markdown(f"""
    <div class="hc-header">
        {logo_html}
        <div class="hc-title-group">
            <h1>HayCash ToolBox</h1>
            <p>Plataforma de Operaciones Financieras</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 7. RENDER GRID ---
cols = st.columns(3) # 3 Column Layout is standard and professional

for i, a in enumerate(apps):
    col = cols[i % 3]
    
    name = a.get("name", "Module")
    # Clean Icon Selection
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"

    with col:
        # 1. The Glass Visuals
        st.markdown(f"""
            <div class="glass-card">
                <div>
                    <div class="icon-circle">{icon}</div>
                    <div class="card-title">{name}</div>
                    <div class="card-sub">Módulo de {name.lower()}.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 2. The Button (Positioned via margin-top negative to sit inside/below card)
        # We move it up visually to dock it with the card
        st.markdown("<div style='margin-top: -65px; padding: 0 25px; position: relative; z-index: 99;'>", unsafe_allow_html=True)
        
        if st.button("ABRIR", key=f"btn_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                safe_navigate(target, name)
                
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 3. Spacer for grid
        st.markdown("<div style='margin-bottom: 30px'></div>", unsafe_allow_html=True)
