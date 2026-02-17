import base64
import time
import os
import sys
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- 0. CRITICAL SAFETY LOCK (PREVENTS WHITE SCREEN) ---
# This forces the app to always reset its brain to the main folder
# before doing anything else.
try:
    PROJECT_ROOT = Path(__file__).resolve().parent
    if os.getcwd() != str(PROJECT_ROOT):
        os.chdir(PROJECT_ROOT)
    # Ensure the root is in the python path so imports work
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
except Exception:
    pass

# --- 1. CORE CONFIGURATION ---
st.set_page_config(
    page_title="HayCash Terminal",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"  # Changed to collapsed since we are hiding it
)

require_shared_password()

ASSETS = PROJECT_ROOT / "assets"

# --- 2. ASSET & LOGIC LOADING ---
def b64(path: Path) -> str:
    if not path.exists(): return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    try:
        cfg_path = PROJECT_ROOT / "apps.yaml"
        if not cfg_path.exists(): return []
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return cfg.get("apps", [])
    except Exception as e:
        st.error(f"Registry Error: {e}")
        return []

def safe_navigate(page_path, app_name):
    """
    Shows a loading spinner and handles the transition safely.
    """
    try:
        # 1. Visual Loading Indicator
        with st.spinner(f"🚀 Initializing {app_name} protocol..."):
            time.sleep(0.4)  # Small delay for visual feedback
            
        # 2. Force Directory Reset BEFORE switching
        # This double-checks we are in the root before the jump
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)
            
        # 3. Go
        st.switch_page(page_path)
        
    except Exception as e:
        st.error(f"Navigation Failed: {e}")

# --- 3. LOAD DATA ---
apps = load_registry()
logo_b64 = b64(ASSETS / "haycash_logo.jpg")

# --- 4. NAVIGATION MAP ---
PAGE_BY_ID = {
    "cdf_isaac": "pages/01_Lector_CSF.py",
    "diegobbva": "pages/02_CSV_a_TXT_BBVA.py",
    "analisis_leads": "pages/03_Reporte_Interactivo_de_Leads.py",
    "factoraje": "pages/04_Factoraje.py",
    "lector_edocat": "pages/05_Lector_edocat.py",
    "reporte_consejo": "pages/06_reporte_consejo.py",
    "lector_contrato": "pages/07_lector_contrato.py",
}

# --- 5. THE "AMEX OBSIDIAN" ENGINE (CSS) ---
st.markdown(f"""
    <style>
        /* IMPORT PREMIUM FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap');
        
        /* GLOBAL RESET */
        html, body, [class*="css"] {{
            font-family: 'Manrope', sans-serif;
            -webkit-font-smoothing: antialiased;
        }}

        /* APP BACKGROUND: Deep Navy Obsidian */
        .stApp {{
            background-color: #0B0E14;
            background-image: 
                radial-gradient(at 0% 0%, rgba(49, 66, 112, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(255, 186, 0, 0.05) 0px, transparent 50%);
            background-attachment: fixed;
        }}

        /* HIDE STREAMLIT CHROME & SIDEBAR COMPLETELY */
        [data-testid="stSidebarNav"], 
        [data-testid="collapsedControl"],
        [data-testid="stSidebar"],
        header[data-testid="stHeader"] {{
            display: none !important;
        }}

        /* --- HERO SECTION --- */
        .block-container {{
            padding-top: 3rem !important;
            max-width: 1400px !important;
        }}
        
        .dashboard-header {{
            margin-bottom: 60px;
            text-align: center; /* Centered for main dashboard impact */
        }}
        .welcome-eyebrow {{
            color: #FFBA00;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-bottom: 15px;
        }}
        .welcome-title {{
            color: #FFFFFF;
            font-size: 4rem;
            font-weight: 800;
            line-height: 1.1;
            letter-spacing: -0.03em;
        }}
        .welcome-subtitle {{
            color: #64748B;
            font-size: 1.25rem;
            font-weight: 400;
            margin-top: 20px;
            max-width: 700px;
            margin-left: auto;
            margin-right: auto;
        }}

        /* --- THE CARD GRID --- */
        .fin-card {{
            background: #11151E;
            border: 1px solid #1E232F;
            border-radius: 16px;
            padding: 30px;
            position: relative;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        /* Glow Effect on Hover */
        .fin-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, #FFBA00, transparent);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .fin-card:hover {{
            transform: translateY(-5px);
            background: #161B26;
            border-color: #314270;
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.5);
        }}
        
        .fin-card:hover::before {{
            opacity: 1;
        }}

        .icon-box {{
            width: 50px;
            height: 50px;
            background: rgba(49, 66, 112, 0.2);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: #8fa3ff;
            margin-bottom: 25px;
            border: 1px solid rgba(49, 66, 112, 0.3);
        }}

        .fin-card-title {{
            color: #FFF;
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 10px;
        }}

        .fin-card-desc {{
            color: #64748B;
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 30px;
            flex-grow: 1;
        }}

        /* Hide Default Container Borders for cleaner look */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
             border: none !important;
             background: transparent !important;
        }}

        /* STATUS INDICATORS */
        .status-dot {{
            height: 8px;
            width: 8px;
            background-color: #10B981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
        }}
        
        .system-status {{
            position: absolute;
            top: 20px;
            right: 20px;
            color: #64748B;
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            background: rgba(255,255,255,0.03);
            padding: 8px 16px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.05);
        }}

        /* LOGO ON MAIN PAGE (Since sidebar is gone) */
        .main-logo {{
            width: 180px;
            margin-bottom: 30px;
            filter: drop-shadow(0 0 15px rgba(255,255,255,0.1));
        }}

    </style>
""", unsafe_allow_html=True)


# --- 6. MAIN DASHBOARD CONTENT ---

# Status Indicator
st.markdown("""
    <div class="system-status">
        <span class="status-dot"></span> SYSTEM ONLINE
    </div>
""", unsafe_allow_html=True)

# Header Section (Centered)
logo_html = f'<img src="data:image/jpg;base64,{logo_b64}" class="main-logo">' if logo_b64 else ""

st.markdown(f"""
    <div class="dashboard-header">
        {logo_html}
        <div class="welcome-eyebrow">HAYCASH TOOLBOX</div>
        <div class="welcome-title">Centro de Control</div>
        <div class="welcome-subtitle">
            Seleccione un módulo operativo para comenzar. Todas las conexiones son seguras y monitoreadas.
        </div>
    </div>
""", unsafe_allow_html=True)

# Grid Layout
cols = st.columns(3)

for i, a in enumerate(apps):
    col = cols[i % 3]
    
    name = a.get("name", "Module")
    # Icon Logic
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"

    with col:
        # Visual Card
        st.markdown(f"""
            <div class="fin-card">
                <div class="icon-box">{icon}</div>
                <div>
                    <div class="fin-card-title">{name}</div>
                    <div class="fin-card-desc">Acceso autorizado al módulo de {name.lower()}. Procesamiento de datos y reportes en tiempo real.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Action Button (Matches card width)
        if st.button(f"INICIAR {name.upper()}", key=f"dash_{a.get('id')}", use_container_width=True):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                safe_navigate(target, name)
        
        # Spacing
        st.markdown("<div style='margin-bottom: 30px'></div>", unsafe_allow_html=True)
