import base64
import time
import os
import sys
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- 0. CRITICAL PATH FIX (Anti-Crash System) ---
try:
    # We resolve the absolute path of this file to find the true root
    PROJECT_ROOT = Path(__file__).resolve().parent
    
    # Force the working directory to be the project root
    if os.getcwd() != str(PROJECT_ROOT):
        os.chdir(PROJECT_ROOT)
        
    # Add root to python path so imports work correctly
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
except Exception as e:
    # If this fails, we log it but try to continue
    print(f"Path initialization warning: {e}")
    PROJECT_ROOT = Path(".")

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="HayCash ToolBox",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Auth check
require_shared_password()

ASSETS = PROJECT_ROOT / "assets"

# --- 2. LOGIC ---
def b64(path: Path) -> str:
    if not path.exists(): return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    try:
        cfg_path = PROJECT_ROOT / "apps.yaml"
        if not cfg_path.exists(): 
            return []
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        return cfg.get("apps", [])
    except Exception:
        return []

def safe_navigate(page_path, app_name):
    """
    Safely transitions to the new page, ensuring directories are reset.
    """
    try:
        with st.spinner(f"Opening {app_name}..."):
            time.sleep(0.2) # Premium feel delay
        
        # Double check directory before switching
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)
            
        st.switch_page(page_path)
    except Exception as e:
        st.error(f"Unable to launch {app_name}. Error: {e}")

# --- 3. LOAD ASSETS ---
apps = load_registry()
logo_b64 = b64(ASSETS / "haycash_logo.jpg")

# --- 4. NAVIGATION MAP ---
# Ensure these files exist in your 'pages' folder
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

        /* RESET & WALLPAPER */
        html, body, [class*="css"] {{
            font-family: 'SF Pro Display', 'Inter', sans-serif;
            background: #000000;
            color: white;
        }}

        /* Deep Space Gradient Background */
        .stApp {{
            background: radial-gradient(circle at 50% -20%, #1a1f35 0%, #000000 60%);
            background-attachment: fixed;
        }}

        /* --- UI CLEANUP --- */
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"], 
        section[data-testid="stSidebar"],
        header[data-testid="stHeader"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* --- LAYOUT --- */
        .block-container {{
            padding-top: 6vh !important;
            max-width: 1250px !important;
        }}

        /* --- HEADER --- */
        .apple-header {{
            display: flex;
            align-items: center;
            margin-bottom: 70px;
            animation: fadeIn 1s ease-out;
        }}
        
        .logo-mark {{
            width: 72px;
            height: 72px;
            border-radius: 18px;
            box-shadow: 0 4px 30px rgba(0,0,0,0.5);
        }}
        
        .header-text {{
            margin-left: 24px;
        }}
        
        .header-text h1 {{
            font-size: 2.8rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0;
            background: linear-gradient(180deg, #ffffff 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header-text p {{
            color: #64748b;
            font-size: 1.1rem;
            margin: 6px 0 0 0;
            font-weight: 400;
        }}

        /* --- LIQUID GLASS CARDS (BUTTONS) --- */
        
        /* Reset Streamlit button defaults completely */
        div.stButton > button {{
            all: unset; 
            width: 100%;
            height: 220px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            padding: 35px;
            box-sizing: border-box;
            
            /* The Glass Effect */
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            border-radius: 28px;
            
            /* Text Styling */
            color: #f4f4f5;
            font-size: 1.3rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            
            /* Animation Physics */
            transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
            position: relative;
            overflow: hidden;
            cursor: pointer;
        }}
        
        /* HOVER: Moving Rainbow Border */
        div.stButton > button::before {{
            content: "";
            position: absolute;
            top: 50%; left: 50%;
            width: 200%; height: 200%;
            background: conic-gradient(from 0deg, transparent 0deg, #FFBA00 90deg, transparent 180deg);
            transform: translate(-50%, -50%) rotate(0deg);
            opacity: 0;
            transition: opacity 0.4s ease;
            z-index: -1;
            pointer-events: none;
        }}

        /* Inner background to hide the center of the conical gradient */
        div.stButton > button::after {{
            content: "";
            position: absolute;
            inset: 1.5px; /* Border thickness */
            background: rgba(15, 15, 20, 0.85); 
            border-radius: 28px;
            z-index: -1;
        }}

        div.stButton > button:hover {{
            transform: scale(1.02) translateY(-5px);
            box-shadow: 0 30px 60px -12px rgba(0,0,0,0.7);
            border-color: rgba(255,255,255,0.2);
        }}
        
        div.stButton > button:hover::before {{
            opacity: 1;
            animation: rotate 4s linear infinite;
        }}

        /* Text Alignment Fix */
        div.stButton > button p {{
            margin: 0;
            text-align: left;
            width: 100%;
            line-height: 1.4;
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
            <p>Select an application to launch secure protocol.</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 7. RENDER GLASS CARDS ---
cols = st.columns(3)

for i, a in enumerate(apps):
    col = cols[i % 3]
    
    name = a.get("name", "App")
    
    # Icons: Using large emojis/chars for instant visual recognition inside the button
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"

    with col:
        # We format the button text to look like a card: Icon on top, Name below
        # \n\n creates the vertical spacing
        label_text = f"{icon}  \n\n{name}"
        
        if st.button(label_text, key=f"app_{a.get('id')}"):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                safe_navigate(target, name)
            else:
                st.error("Module path not configured.")
        
        st.write("") # Layout spacer
        st.write("")
