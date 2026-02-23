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
        st.exception(e)

require_shared_password()

# --- LOGIN TRANSITION ANIMATION ---
if "login_splash_done" not in st.session_state:
    st.session_state["login_splash_done"] = False

authed = bool(st.session_state.get("auth_ok"))

if authed and not st.session_state["login_splash_done"]:
    logo_path = ASSETS / "haycash_logo.jpg"
    logo_b64_local = b64(logo_path) if logo_path.exists() else ""
    st.markdown(
        f"""
        <style>
          .hc-splash {{ position: fixed; inset: 0; background: #000000; z-index: 999999; display: flex; align-items: center; justify-content: center; perspective: 1000px; animation: hcVoidVanish 1.5s cubic-bezier(0.85, 0, 0.15, 1) forwards; animation-delay: 3.5s; }}
          .hc-core-wrapper {{ position: relative; width: 120px; height: 120px; transform-style: preserve-3d; animation: hcCoreExplode 0.8s cubic-bezier(0.7, 0, 0.84, 0) forwards; animation-delay: 2.8s; }}
          .hc-ring {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 50%; border: 2px solid transparent; box-shadow: 0 0 15px rgba(0, 100, 255, 0.1); }}
          .hc-ring-1 {{ border-top: 2px solid #ffffff; border-bottom: 2px solid #ffffff; width: 100%; height: 100%; animation: hcSpin3D 1.5s linear infinite; filter: drop-shadow(0 0 10px #ffffff); }}
          .hc-ring-2 {{ border-left: 2px solid #007aff; border-right: 2px solid #007aff; width: 140%; height: 140%; top: -20%; left: -20%; animation: hcSpin3DReverse 3s linear infinite; filter: drop-shadow(0 0 15px #007aff); }}
          .hc-ring-3 {{ border: 1px dashed rgba(255, 255, 255, 0.3); width: 220%; height: 220%; top: -60%; left: -60%; animation: hcSpinFlat 8s linear infinite; }}
          .hc-singularity {{ position: absolute; top: 50%; left: 50%; width: 10px; height: 10px; background: #fff; border-radius: 50%; transform: translate(-50%, -50%); box-shadow: 0 0 30px 10px rgba(0, 122, 255, 0.8); animation: hcPulseCore 2s ease-in-out infinite; }}
          .hc-text {{ position: absolute; bottom: -80px; left: 50%; transform: translateX(-50%); color: #fff; font-family: 'SF Pro Display', sans-serif; font-size: 14px; letter-spacing: 4px; text-transform: uppercase; opacity: 0; width: 300px; text-align: center; animation: hcTextFadeIn 1s ease forwards; animation-delay: 0.5s; }}
          @keyframes hcSpin3D {{ 0% {{ transform: rotateX(0deg) rotateY(0deg) rotateZ(0deg); }} 100% {{ transform: rotateX(360deg) rotateY(180deg) rotateZ(360deg); }} }}
          @keyframes hcSpin3DReverse {{ 0% {{ transform: rotateX(0deg) rotateY(0deg) rotateZ(0deg); }} 100% {{ transform: rotateX(-360deg) rotateY(-180deg) rotateZ(-90deg); }} }}
          @keyframes hcSpinFlat {{ 0% {{ transform: rotateZ(0deg); opacity: 0.3; }} 50% {{ opacity: 0.6; }} 100% {{ transform: rotateZ(360deg); opacity: 0.3; }} }}
          @keyframes hcPulseCore {{ 0%, 100% {{ transform: translate(-50%, -50%) scale(1); box-shadow: 0 0 30px 10px rgba(0, 122, 255, 0.6); }} 50% {{ transform: translate(-50%, -50%) scale(1.5); box-shadow: 0 0 50px 20px rgba(0, 180, 255, 0.9); }} }}
          @keyframes hcTextFadeIn {{ to {{ opacity: 0.7; letter-spacing: 6px; }} }}
          @keyframes hcCoreExplode {{ 0% {{ transform: scale(1); filter: brightness(1); }} 40% {{ transform: scale(0.1); filter: brightness(5); }} 50% {{ transform: scale(0.1); filter: brightness(10); opacity: 1; }} 100% {{ transform: scale(20); filter: blur(20px); opacity: 0; }} }}
          @keyframes hcVoidVanish {{ 0% {{ opacity: 1; transform: scale(1); }} 100% {{ opacity: 0; transform: scale(1.2); pointer-events: none; visibility: hidden; }} }}
        </style>
        <div class="hc-splash">
          <div class="hc-core-wrapper">
             <div class="hc-ring hc-ring-1"></div>
             <div class="hc-ring hc-ring-2"></div>
             <div class="hc-ring hc-ring-3"></div>
             <div class="hc-singularity"></div>
          </div>
          <div class="hc-text">Initializing Secure Protocol</div>
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

# --- 5. THE CUPERTINO GLASS ENGINE ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;500;700;800&family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] {{ font-family: 'SF Pro Display', 'Inter', sans-serif; background: #050505; color: white; overflow-x: hidden; }}
        .stApp {{ background: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #000000 80%); background-attachment: fixed; }}
        .stApp::before {{ content: ""; position: absolute; top: 0; left: 0; right: 0; height: 100vh; background-image: radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 3px), radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 2px), radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 3px); background-size: 550px 550px, 350px 350px, 250px 250px; background-position: 0 0, 40px 60px, 130px 270px; opacity: 0.4; animation: starDrift 120s linear infinite; z-index: 0; pointer-events: none; }}
        @keyframes starDrift {{ from {{ transform: translateY(0); }} to {{ transform: translateY(-550px); }} }}
        [data-testid="stSidebar"], [data-testid="collapsedControl"], section[data-testid="stSidebar"], header[data-testid="stHeader"] {{ display: none !important; visibility: hidden !important; }}
        .block-container {{ padding-top: 8vh !important; max-width: 1250px !important; position: relative; z-index: 10; }}

        /* EXECUTIVE TOP BAR */
        .hc-homebar {{ width: 100%; background: rgba(35, 38, 55, 0.55); border: 1px solid rgba(255,255,255,0.10); border-radius: 22px; padding: 20px 26px; display: flex; align-items: center; justify-content: space-between; backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); box-shadow: 0 18px 50px rgba(0,0,0,0.55); margin-bottom: 70px; opacity: 0; animation: heroEntrance 1s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; animation-delay: 3.6s; }}
        .hc-homebar-title {{ font-size: 3.1rem; font-weight: 800; letter-spacing: -1.5px; margin: 0; background: linear-gradient(135deg, #ffffff 10%, #b9bcc6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 10px 40px rgba(0,0,0,0.6); line-height: 1.05; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .hc-homebar-logo {{ width: 380px; height: 100px; background-repeat: no-repeat; background-position: right center; background-size: contain; opacity: 0.92; flex: 0 0 auto; }}
        .hc-homebar-accent {{ height: 3px; width: 100%; background: linear-gradient(90deg, rgba(0,122,255,0) 0%, rgba(0,122,255,0.8) 25%, rgba(0,255,255,1) 45%, #ffffff 50%, rgba(0,255,255,1) 55%, rgba(0,122,255,0.8) 75%, rgba(0,122,255,0) 100%); background-size: 200% 100%; border-radius: 999px; margin-top: -52px; margin-bottom: 90px; box-shadow: 0 0 20px 2px rgba(0,255,255,0.5), 0 0 40px 5px rgba(0,122,255,0.3); opacity: 0.9; animation: laserSweep 4s ease-in-out infinite; }}

        /* GLASS CARDS - WIDTH FIX */
        div.stButton > button {{
            all: unset;
            display: flex !important;
            flex-direction: column !important;
            width: 100% !important;
            height: 250px !important; /* LOCKED HEIGHT */
            min-height: 250px !important;
            max-height: 250px !important;
            background: rgba(20, 20, 30, 0.6) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border-radius: 24px !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            position: relative !important;
            cursor: pointer !important;
            padding: 40px 30px !important;
            box-sizing: border-box !important;
            opacity: 0;
            animation: cardFloatUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
            transition: transform 0.3s ease, border-color 0.3s ease !important;
        }}

        div.stButton:nth-of-type(1) > button {{ animation-delay: 3.7s; }}
        div.stButton:nth-of-type(2) > button {{ animation-delay: 3.8s; }}
        div.stButton:nth-of-type(3) > button {{ animation-delay: 3.9s; }}
        div.stButton:nth-of-type(4) > button {{ animation-delay: 4.0s; }}
        div.stButton:nth-of-type(5) > button {{ animation-delay: 4.1s; }}

        div.stButton > button:hover {{ transform: translateY(-8px) scale(1.02); border-color: rgba(0, 122, 255, 0.6) !important; }}

        /* INNER CONTENT ALIGNMENT */
        div.stButton > button p {{
            margin: 0 !important;
            padding: 0 !important;
            color: #f5f5f7 !important;
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
            text-align: left !important;
            white-space: normal !important;
            display: -webkit-box !important;
            -webkit-line-clamp: 3 !important;
            -webkit-box-orient: vertical !important;
            overflow: hidden !important;
            width: 100% !important;
        }}

        @keyframes heroEntrance {{ from {{ opacity: 0; transform: translateY(20px); filter: blur(10px); }} to {{ opacity: 1; transform: translateY(0); filter: blur(0px); }} }}
        @keyframes cardFloatUp {{ from {{ opacity: 0; transform: translateY(50px) scale(0.95); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
        @keyframes laserSweep {{ 0% {{ background-position: 0% center; }} 50% {{ background-position: 100% center; }} 100% {{ background-position: 0% center; }} }}
    </style>
""", unsafe_allow_html=True)

# --- 6. RENDER HEADER ---
topbar_logo_style = f'style="background-image:url(data:image/jpg;base64,{logo_b64});"' if logo_b64 else ""
try:
    st.markdown(f"""
        <div class="hc-homebar">
            <div class="hc-homebar-left">
                <div class="hc-homebar-title">HayCash ToolBox</div>
            </div>
            <div class="hc-homebar-logo" {topbar_logo_style}></div>
        </div>
        <div class="hc-homebar-accent"></div>
    """, unsafe_allow_html=True)

    # --- 7. RENDER GLASS CARDS ---
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
            # We combine icon and name in a single line. The CSS line-clamping manages the wrap.
            if st.button(f"{icon}  \n\n{name}", key=f"app_{a.get('id')}"):
                target = PAGE_BY_ID.get(a.get("id"))
                if target:
                    safe_navigate(target, name)
                else:
                    st.error(f"Module '{name}' not linked.")
            st.write("")
except Exception as e:
    st.error("App crashed while rendering.")
    st.exception(e)
