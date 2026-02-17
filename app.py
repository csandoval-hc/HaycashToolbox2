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
    page_title="HayCash ToolBox",
    page_icon="💎",
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
        with st.spinner(f"Opening {app_name}..."):
            time.sleep(0.3)
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)
        st.switch_page(page_path)
    except Exception as e:
        st.error(f"Navigation error: {e}")

# --- 3. ASSETS ---
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

# --- 5. THE "CUPERTINO GLASS" ENGINE ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;500;700&family=Inter:wght@400;600&display=swap');

        /* RESET */
        html, body, [class*="css"] {{
            font-family: 'SF Pro Display', 'Inter', sans-serif;
            background: #000000;
            color: white;
        }}

        /* WALLPAPER: Deep Space Gradient */
        .stApp {{
            background: radial-gradient(circle at 50% -20%, #2b3044 0%, #06070a 60%);
            background-attachment: fixed;
        }}

        /* --- UI REMOVAL --- */
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"], 
        section[data-testid="stSidebar"],
        header[data-testid="stHeader"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0px !important;
            height: 0px !important;
        }}

        /* --- LAYOUT --- */
        .block-container {{
            padding-top: 5vh !important;
            max-width: 1200px !important;
        }}

        /* --- HEADER --- */
        .apple-header {{
            display: flex;
            align-items: center;
            margin-bottom: 60px;
            animation: fadeIn 1s ease-out;
        }}
        
        .logo-mark {{
            width: 64px;
            height: 64px;
            border-radius: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        
        .header-text {{
            margin-left: 20px;
        }}
        
        .header-text h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0;
            background: linear-gradient(180deg, #fff 0%, #a1a1aa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header-text p {{
            color: #71717a;
            font-size: 1rem;
            margin: 5px 0 0 0;
        }}

        /* --- THE MAGIC BUTTONS (CARDS) --- */
        /* We turn the button element itself into the card */
        
        div.stButton > button {{
            all: unset; /* Reset default streamlit styles */
            
            /* Card Dimensions & Layout */
            width: 100%;
            height: 200px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            padding: 30px;
            box-sizing: border-box;
            
            /* Glassmorphism */
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            
            /* Typography inside button */
            color: #f4f4f5;
            font-size: 1.2rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            
            /* Physics */
            transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
            position: relative;
            overflow: hidden;
            cursor: pointer;
        }}
        
        /* HOVER EFFECT: The Rainbow Border */
        /* We use a pseudo-element gradient that rotates behind the card */
        div.stButton > button::before {{
            content: "";
            position: absolute;
            top: 50%; left: 50%;
            width: 150%; height: 150%;
            background: conic-gradient(from 0deg, transparent 0deg, #FFBA00 90deg, transparent 180deg);
            transform: translate(-50%, -50%) rotate(0deg);
            opacity: 0;
            transition: opacity 0.3s ease;
            z-index: -1;
            pointer-events: none;
        }}

        div.stButton > button::after {{
            content: "";
            position: absolute;
            inset: 1px; /* The border width */
            background: rgba(20, 20, 25, 0.9); /* Inner card background */
            border-radius: 24px;
            z-index: -1;
        }}

        div.stButton > button:hover {{
            transform: scale(1.02);
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.6);
        }}
        
        div.stButton > button:hover::before {{
            opacity: 1;
            animation: rotate 3s linear infinite;
        }}

        /* TEXT STYLING INSIDE BUTTON */
        /* Streamlit buttons force text centering, we force it back */
        div.stButton > button p {{
            margin: 0;
            text-align: left;
            width: 100%;
        }}

        @keyframes rotate {{
            from {{ transform: translate(-50%, -50%) rotate(0deg); }}
            to {{ transform: translate(-50%, -50%) rotate(360deg); }}
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

    </style>
""", unsafe_allow_html=True)

# --- 6. RENDER HEADER ---
logo_img = f'<img src="data:image/jpg;base64,{logo_b64}" class="logo-mark">' if logo_b64 else ""

st.markdown(f"""
    <div class="apple-header">
        {logo_img}
        <div class="header-text">
            <h1>HayCash ToolBox</h1>
            <p>Select an application to launch.</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 7. RENDER CARDS (AS BUTTONS) ---
cols = st.columns(3)

for i, a in enumerate(apps):
    col = cols[i % 3]
    
    name = a.get("name", "App")
    
    # Icons (Simple unicode for speed/reliability inside buttons)
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"

    with col:
        # We put the icon AND name inside the button label
        # The CSS handles the layout to look like a card
        label_text = f"{icon}  \n\n{name}"
        
        if st.button(label_text, key=f"app_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                safe_navigate(target, name)
        
        st.write("") # Spacer
        st.write("")
