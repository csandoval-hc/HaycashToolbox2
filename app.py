import base64
import time
import os
import sys
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- 0. SAFETY LOCK ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent
    if os.getcwd() != str(PROJECT_ROOT):
        os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
except Exception:
    pass

# --- 1. CONFIG ---
st.set_page_config(
    page_title="HayCash Terminal",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

require_shared_password()

ASSETS = PROJECT_ROOT / "assets"

# --- 2. LOGIC ---
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
        with st.spinner(f"AUTHENTICATING {app_name.upper()}..."):
            time.sleep(0.3)
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)
        st.switch_page(page_path)
    except Exception as e:
        st.error(f"Handshake failed: {e}")

# --- 3. DATA ---
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

# --- 5. THE "CITADEL" DESIGN SYSTEM ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        /* BASE */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: #050505;
            color: #E2E8F0;
        }}
        
        /* HIDE STREAMLIT UI */
        [data-testid="stSidebarNav"], [data-testid="collapsedControl"], header[data-testid="stHeader"] {{
            display: none !important;
        }}

        /* BACKGROUND */
        .stApp {{
            background: 
                radial-gradient(circle at 15% 50%, rgba(49, 66, 112, 0.12), transparent 25%),
                radial-gradient(circle at 85% 30%, rgba(255, 186, 0, 0.08), transparent 25%);
            background-color: #080a0f;
        }}

        /* CONTAINER FIX */
        .block-container {{
            padding-top: 0 !important;
            padding-bottom: 5rem !important;
            max-width: 1400px !important;
        }}

        /* --- 1. TOP NAVIGATION BAR --- */
        .top-nav {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.5rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 4rem;
        }}
        .nav-left {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .nav-logo {{
            height: 32px;
            width: auto;
            border-radius: 6px;
        }}
        .nav-title {{
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 1.1rem;
            color: #fff;
            letter-spacing: -0.02em;
        }}
        .status-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #10B981;
            background: rgba(16, 185, 129, 0.1);
            padding: 6px 12px;
            border-radius: 100px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .status-dot {{
            width: 6px; height: 6px;
            background: #10B981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10B981;
        }}

        /* --- 2. HERO SECTION --- */
        .hero-section {{
            margin-bottom: 3.5rem;
        }}
        .hero-eyebrow {{
            color: #FFBA00;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            margin-bottom: 1rem;
        }}
        .hero-title {{
            font-size: 3.5rem;
            font-weight: 800;
            color: white;
            line-height: 1.1;
            letter-spacing: -0.03em;
            margin-bottom: 1rem;
            background: linear-gradient(to right, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .hero-sub {{
            font-size: 1.1rem;
            color: #64748B;
            max-width: 600px;
            line-height: 1.6;
        }}

        /* --- 3. CARD GRID SYSTEM --- */
        /* Card Container */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border: none !important;
            background: transparent !important;
        }}
        
        .module-card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px;
            height: 240px; /* Fixed height for uniformity */
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        
        .module-card:hover {{
            background: rgba(255, 255, 255, 0.05);
            border-color: #FFBA00;
            transform: translateY(-4px);
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.5);
        }}

        .card-icon {{
            font-size: 24px;
            background: rgba(49, 66, 112, 0.3);
            width: 48px; 
            height: 48px;
            display: flex; 
            align-items: center; 
            justify-content: center;
            border-radius: 10px;
            border: 1px solid rgba(49, 66, 112, 0.5);
            margin-bottom: 1rem;
            color: #fff;
        }}

        .card-title {{
            color: #fff;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        
        .card-desc {{
            color: #94a3b8;
            font-size: 0.85rem;
            line-height: 1.5;
        }}

        /* --- 4. BUTTON PHYSICS (THE FIX) --- */
        /* Target the specific buttons inside columns */
        div.stButton > button {{
            width: 100%;
            background-color: transparent !important;
            border: 1px solid #334155 !important;
            color: #94a3b8 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            padding: 0.6rem 1rem !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        
        /* Hover State - High Contrast */
        div.stButton > button:hover {{
            background-color: #FFBA00 !important;
            border-color: #FFBA00 !important;
            color: #000000 !important; /* Dark text on gold background */
            box-shadow: 0 0 15px rgba(255, 186, 0, 0.4) !important;
            transform: scale(1.02);
        }}
        
        /* Active/Focus State */
        div.stButton > button:active {{
            background-color: #e6a700 !important;
            transform: scale(0.98);
        }}

    </style>
""", unsafe_allow_html=True)


# --- 6. RENDER UI ---

# 6.1 TOP BAR (Fixed Navigation Look)
st.markdown(f"""
    <div class="top-nav">
        <div class="nav-left">
            <img src="data:image/jpg;base64,{logo_b64}" class="nav-logo">
            <div class="nav-title">HayCash Terminal</div>
        </div>
        <div class="status-badge">
            <div class="status-dot"></div>
            SYSTEM SECURE
        </div>
    </div>
""", unsafe_allow_html=True)

# 6.2 HERO SECTION
st.markdown("""
    <div class="hero-section">
        <div class="hero-eyebrow">Enterprise Workspace</div>
        <div class="hero-title">Financial Operations<br>Command Center</div>
        <div class="hero-sub">
            Centralized access to HayCash analytic engines. Select a module below to initialize secure environment.
        </div>
    </div>
""", unsafe_allow_html=True)

# 6.3 MODULE GRID
cols = st.columns(4) # Using 4 columns for a wider, cleaner spread

for i, a in enumerate(apps):
    col = cols[i % 4]
    
    name = a.get("name", "Module")
    
    # Mapped Icons
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"

    with col:
        # Card Visuals
        st.markdown(f"""
            <div class="module-card">
                <div>
                    <div class="card-icon">{icon}</div>
                    <div class="card-title">{name}</div>
                    <div class="card-desc">Initialize {name.lower()} module protocol.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Action Button (Placed physically outside the HTML card but visually aligned)
        st.markdown("<div style='margin-top: -50px; padding: 0 20px; position: relative; z-index: 2;'>", unsafe_allow_html=True)
        if st.button("LAUNCH", key=f"launch_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                safe_navigate(target, name)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Spacer
        st.markdown("<div style='margin-bottom: 2rem'></div>", unsafe_allow_html=True)
