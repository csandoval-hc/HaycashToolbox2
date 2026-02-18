import base64
import time
import os
import sys
from pathlib import Path
import streamlit as st
import yaml

# --- 0. CRITICAL SYSTEM SETUP ---
try:
    CURRENT_FILE = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_FILE.parent

    if os.getcwd() != str(PROJECT_ROOT):
        os.chdir(PROJECT_ROOT)

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

except Exception as e:
    print(f"Init Warning: {e}")
    PROJECT_ROOT = Path(".")

from simple_auth import require_shared_password

# --- 1. APP CONFIGURATION ---
st.set_page_config(
    page_title="HayCash ToolBox",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

ASSETS = PROJECT_ROOT / "assets"

# --- 2. CORE UTILITIES ---
def b64(path: Path) -> str:
    if not path.exists(): 
        return ""
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
    try:
        with st.spinner(f"Accessing {app_name}..."):
            time.sleep(0.3) 
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)
        target_file = (PROJECT_ROOT / page_path).resolve()
        if not target_file.exists():
            st.error(f"Missing page file: {page_path}")
            return
        st.switch_page(page_path)
    except Exception as e:
        st.error(f"Navigation Error: {e}")

# Authentication Barrier
require_shared_password()

# --- LOGIN TRANSITION ANIMATION (HIGH-FIDELITY OVERHAUL) ---
if "login_splash_done" not in st.session_state:
    st.session_state["login_splash_done"] = False

authed = bool(st.session_state.get("auth_ok"))

if authed and not st.session_state["login_splash_done"]:
    logo_path = ASSETS / "haycash_logo.jpg"
    logo_b64_local = b64(logo_path) if logo_path.exists() else ""

    st.markdown(
        f"""
        <style>
          .hc-splash {{
            position: fixed;
            inset: 0;
            background: #000000;
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: hcScreenExit 0.8s cubic-bezier(0.77, 0, 0.175, 1) forwards;
            animation-delay: 2.2s;
          }}

          .hc-splash-inner {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 300px;
            height: 300px;
          }}

          /* The Quantum Orb: Multi-layered glow */
          .hc-orb {{
            position: absolute;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: #ffffff;
            box-shadow: 
                0 0 20px #fff,
                0 0 40px #1a6dff,
                0 0 80px #1a6dff;
            animation: 
                hcOrbPulse 1.8s cubic-bezier(0.45, 0, 0.55, 1) infinite,
                hcOrbImplode 0.6s cubic-bezier(0.6, -0.28, 0.735, 0.045) forwards;
            animation-delay: 0s, 1.4s;
          }}

          .hc-logo {{
            width: 140px;
            height: 140px;
            border-radius: 30px;
            background-image: url("data:image/jpg;base64,{logo_b64_local}");
            background-size: cover;
            background-position: center;
            opacity: 0;
            transform: scale(0.5) translateY(20px);
            filter: blur(10px);
            animation: hcLogoReveal 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
            animation-delay: 1.6s;
            box-shadow: 0 20px 50px rgba(0,0,0,0.8);
            border: 1px solid rgba(255,255,255,0.2);
          }}

          @keyframes hcOrbPulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; filter: brightness(1); }}
            50% {{ transform: scale(1.1); opacity: 0.8; filter: brightness(1.4); }}
          }}

          @keyframes hcOrbImplode {{
            0% {{ transform: scale(1); filter: blur(0px); }}
            100% {{ transform: scale(0); filter: blur(20px); opacity: 0; }}
          }}

          @keyframes hcLogoReveal {{
            to {{
              opacity: 1;
              transform: scale(1) translateY(0);
              filter: blur(0px);
            }}
          }}

          @keyframes hcScreenExit {{
            to {{
              background: transparent;
              backdrop-filter: blur(0px);
              transform: translateY(-100%);
              pointer-events: none;
            }}
          }}
        </style>

        <div class="hc-splash">
          <div class="hc-splash-inner">
            <div class="hc-orb"></div>
            <div class="hc-logo"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["login_splash_done"] = True

# --- 3. LOAD DATA & ASSETS ---
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

# --- 5. THE CUPERTINO GLASS ENGINE (REFINED PHYSICS) ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;500;700&family=Inter:wght@400;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'SF Pro Display', 'Inter', sans-serif;
            background: #000000;
            color: white;
        }}

        .stApp {{
            background: radial-gradient(circle at 50% -20%, #1c1c2e 0%, #000000 70%);
            background-attachment: fixed;
        }}

        [data-testid="stSidebar"], [data-testid="collapsedControl"], header[data-testid="stHeader"] {{
            display: none !important;
        }}

        .block-container {{
            padding-top: 8vh !important;
            max-width: 1250px !important;
        }}

        /* --- STAGGERED ENTRANCE ANIMATION --- */
        .apple-header {{
            display: flex;
            align-items: center;
            margin-bottom: 70px;
            animation: slideUpFade 1s cubic-bezier(0.2, 0.8, 0.2, 1) both;
            animation-delay: 2.5s; /* Wait for splash */
        }}
        
        @keyframes slideUpFade {{
            from {{ opacity: 0; transform: translateY(30px); filter: blur(10px); }}
            to {{ opacity: 1; transform: translateY(0); filter: blur(0px); }}
        }}

        .logo-mark {{
            width: 72px;
            height: 72px;
            border-radius: 18px;
            box-shadow: 0 4px 30px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .header-text h1 {{
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: -0.04em;
            margin: 0;
            background: linear-gradient(180deg, #ffffff 0%, #a1a1a6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        /* --- BUTTONS: GLASSMORPHISM 2.0 --- */
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
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 32px;
            color: #f5f5f7;
            font-size: 1.3rem;
            font-weight: 600;
            transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            overflow: hidden;
            animation: slideUpFade 1s cubic-bezier(0.2, 0.8, 0.2, 1) both;
        }}

        /* Individual button stagger */
        div.stButton:nth-child(1) > button {{ animation-delay: 2.6s; }}
        div.stButton:nth-child(2) > button {{ animation-delay: 2.7s; }}
        div.stButton:nth-child(3) > button {{ animation-delay: 2.8s; }}

        div.stButton > button:hover {{
            transform: scale(1.03) translateY(-8px);
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 0 40px 80px rgba(0,0,0,0.6);
        }}

        /* Subtle "Active" Press Effect */
        div.stButton > button:active {{
            transform: scale(0.97);
            transition: 0.1s;
        }}

    </style>
""", unsafe_allow_html=True)

# --- 6. RENDER HEADER ---
logo_img = f'<img src="data:image/jpg;base64,{logo_b64}" class="logo-mark">' if logo_b64 else ""

try:
    st.markdown(f"""
        <div class="apple-header">
            {logo_img}
            <div class="header-text" style="margin-left:24px;">
                <h1>HayCash ToolBox</h1>
                <p style="color:#86868b; font-size:1.1rem; margin:6px 0;">Intelligence Layer 1.0</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    for i, a in enumerate(apps):
        col = cols[i % 3]
        name = a.get("name", "App")
        icon = "⚡"
        if "CSF" in name: icon = "🧾"
        elif "BBVA" in name: icon = "🏦"
        elif "Leads" in name: icon = "📊"
        elif "Factoraje" in name: icon = "💳"
        elif "Edocat" in name: icon = "📄"
        elif "Consejo" in name: icon = "📈"
        elif "Contrato" in name: icon = "📝"

        with col:
            label_text = f"{icon}  \n\n{name}"
            if st.button(label_text, key=f"app_{a.get('id')}"):
                target = PAGE_BY_ID.get(a.get("id"))
                if target:
                    safe_navigate(target, name)
            st.write("") 

except Exception as e:
    st.error("UI Render Exception")
    st.exception(e)
