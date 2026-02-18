import base64
import time
import os
import sys
from pathlib import Path
import streamlit as st
import yaml

# --- 0. CRITICAL SYSTEM SETUP ---
# This ensures the app always runs from the correct root folder
try:
    # 1. Identify where this file (app.py) is located
    CURRENT_FILE = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_FILE.parent

    # 2. Force the working directory to match
    if os.getcwd() != str(PROJECT_ROOT):
        os.chdir(PROJECT_ROOT)

    # 3. Add to Python path so imports like 'simple_auth' work
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

except Exception as e:
    # Fallback if filesystem is locked (rare)
    print(f"Init Warning: {e}")
    PROJECT_ROOT = Path(".")

# IMPORTANT FIX: import AFTER sys.path is corrected (prevents white screen/crash)
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
    """Converts an image file to a base64 string for HTML embedding."""
    if not path.exists(): 
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    """Loads the list of available apps from apps.yaml."""
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
    Handles the transition to a sub-app safely.
    """
    try:
        with st.spinner(f"Accessing {app_name}..."):
            time.sleep(0.3)  # Cinematic delay

        # Double check we are anchored at root before jumping
        if os.getcwd() != str(PROJECT_ROOT):
            os.chdir(PROJECT_ROOT)

        # IMPORTANT FIX: prevent blank/failed transitions if the page file is missing
        target_file = (PROJECT_ROOT / page_path).resolve()
        if not target_file.exists():
            st.error(f"Missing page file: {page_path}")
            return

        st.switch_page(page_path)

    except Exception as e:
        st.error(f"Navigation Error: {e}")
        st.exception(e)

# Authentication Barrier
require_shared_password()

# --- LOGIN TRANSITION ANIMATION (CINEMA GRADE) ---
# Shows once per session after auth, then disappears.
if "login_splash_done" not in st.session_state:
    st.session_state["login_splash_done"] = False

authed = bool(st.session_state.get("auth_ok"))

if authed and not st.session_state["login_splash_done"]:
    logo_path = ASSETS / "haycash_logo.jpg"
    logo_b64_local = b64(logo_path) if logo_path.exists() else ""

    st.markdown(
        f"""
        <style>
          /* --- THE VOID CONTAINER --- */
          .hc-splash {{
            position: fixed;
            inset: 0;
            background: #000000;
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
            perspective: 1000px; /* Enable 3D space */
            animation: hcVoidVanish 1.5s cubic-bezier(0.85, 0, 0.15, 1) forwards;
            animation-delay: 3.5s; /* Total sequence length */
          }}

          /* --- THE HYPER-CORE (GYROSCOPE) --- */
          .hc-core-wrapper {{
            position: relative;
            width: 120px;
            height: 120px;
            transform-style: preserve-3d;
            animation: hcCoreExplode 0.8s cubic-bezier(0.7, 0, 0.84, 0) forwards;
            animation-delay: 2.8s;
          }}

          /* Common Ring Style */
          .hc-ring {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            border-radius: 50%;
            border: 2px solid transparent;
            box-shadow: 0 0 15px rgba(0, 100, 255, 0.1);
          }}

          /* Inner Ring - Fast & Bright */
          .hc-ring-1 {{
            border-top: 2px solid #ffffff;
            border-bottom: 2px solid #ffffff;
            width: 100%; height: 100%;
            animation: hcSpin3D 1.5s linear infinite;
            filter: drop-shadow(0 0 10px #ffffff);
          }}

          /* Middle Ring - Blue & Tilted */
          .hc-ring-2 {{
            border-left: 2px solid #007aff;
            border-right: 2px solid #007aff;
            width: 140%; height: 140%;
            top: -20%; left: -20%;
            animation: hcSpin3DReverse 3s linear infinite;
            filter: drop-shadow(0 0 15px #007aff);
          }}

          /* Outer Ring - Slow & Deep */
          .hc-ring-3 {{
            border: 1px dashed rgba(255, 255, 255, 0.3);
            width: 220%; height: 220%;
            top: -60%; left: -60%;
            animation: hcSpinFlat 8s linear infinite;
          }}

          /* The Singularity (Center Dot) */
          .hc-singularity {{
            position: absolute;
            top: 50%; left: 50%;
            width: 10px; height: 10px;
            background: #fff;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 0 30px 10px rgba(0, 122, 255, 0.8);
            animation: hcPulseCore 2s ease-in-out infinite;
          }}

          /* --- TEXT REVEAL --- */
          .hc-text {{
            position: absolute;
            bottom: -80px;
            left: 50%;
            transform: translateX(-50%);
            color: #fff;
            font-family: 'SF Pro Display', sans-serif;
            font-size: 14px;
            letter-spacing: 4px;
            text-transform: uppercase;
            opacity: 0;
            width: 300px;
            text-align: center;
            animation: hcTextFadeIn 1s ease forwards;
            animation-delay: 0.5s;
          }}

          /* --- ANIMATION KEYFRAMES --- */
          
          /* 3D Spinning */
          @keyframes hcSpin3D {{
            0% {{ transform: rotateX(0deg) rotateY(0deg) rotateZ(0deg); }}
            100% {{ transform: rotateX(360deg) rotateY(180deg) rotateZ(360deg); }}
          }}

          @keyframes hcSpin3DReverse {{
            0% {{ transform: rotateX(0deg) rotateY(0deg) rotateZ(0deg); }}
            100% {{ transform: rotateX(-360deg) rotateY(-180deg) rotateZ(-90deg); }}
          }}

          @keyframes hcSpinFlat {{
            0% {{ transform: rotateZ(0deg); opacity: 0.3; }}
            50% {{ opacity: 0.6; }}
            100% {{ transform: rotateZ(360deg); opacity: 0.3; }}
          }}

          @keyframes hcPulseCore {{
            0%, 100% {{ transform: translate(-50%, -50%) scale(1); box-shadow: 0 0 30px 10px rgba(0, 122, 255, 0.6); }}
            50% {{ transform: translate(-50%, -50%) scale(1.5); box-shadow: 0 0 50px 20px rgba(0, 180, 255, 0.9); }}
          }}

          @keyframes hcTextFadeIn {{
            to {{ opacity: 0.7; letter-spacing: 6px; }}
          }}

          /* The Big Bang: Core collapses then explodes */
          @keyframes hcCoreExplode {{
            0% {{ transform: scale(1); filter: brightness(1); }}
            40% {{ transform: scale(0.1); filter: brightness(5); }} /* Implode */
            50% {{ transform: scale(0.1); filter: brightness(10); opacity: 1; }} /* Critical Mass */
            100% {{ transform: scale(20); filter: blur(20px); opacity: 0; }} /* Big Bang */
          }}

          /* The Curtain Lift */
          @keyframes hcVoidVanish {{
            0% {{ opacity: 1; transform: scale(1); }}
            100% {{ opacity: 0; transform: scale(1.2); pointer-events: none; visibility: hidden; }}
          }}
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

    # Mark as shown so it doesn't repeat on every rerun
    st.session_state["login_splash_done"] = True

# --- 3. LOAD DATA & ASSETS ---
apps = load_registry()
logo_b64 = b64(ASSETS / "haycash_logo.jpg")

# --- 4. NAVIGATION MAP ---
# This links the ID in apps.yaml to the actual physical file
PAGE_BY_ID = {
    "cdf_isaac": "pages/01_Lector_CSF.py",
    "diegobbva": "pages/02_CSV_a_TXT_BBVA.py",
    "analisis_leads": "pages/03_Reporte_Interactivo_de_Leads.py",
    "factoraje": "pages/04_Factoraje.py",
    "lector_edocat": "pages/05_Lector_edocat.py",
    "reporte_consejo": "pages/06_reporte_consejo.py",
    "lector_contrato": "pages/07_lector_contrato.py",
}

# --- 5. THE CUPERTINO GLASS ENGINE (ULTRA-PREMIUM) ---
st.markdown(f"""
    <style>
        /* Fonts */
        @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;500;700&family=Inter:wght@400;600&display=swap');

        /* Global Reset */
        html, body, [class*="css"] {{
            font-family: 'SF Pro Display', 'Inter', sans-serif;
            background: #050505;
            color: white;
            overflow-x: hidden;
        }}

        /* --- THE DEEP SPACE BACKGROUND (CSS STARS) --- */
        .stApp {{
            background: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #000000 80%);
            background-attachment: fixed;
        }}
        
        .stApp::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 100vh;
            background-image: 
                radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 3px),
                radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 2px),
                radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 3px);
            background-size: 550px 550px, 350px 350px, 250px 250px;
            background-position: 0 0, 40px 60px, 130px 270px;
            opacity: 0.4;
            animation: starDrift 120s linear infinite;
            z-index: 0;
            pointer-events: none;
        }}

        @keyframes starDrift {{
            from {{ transform: translateY(0); }}
            to {{ transform: translateY(-550px); }}
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
            padding-top: 8vh !important;
            max-width: 1250px !important;
            position: relative;
            z-index: 10;
        }}

        /* --- HEADER --- */
        .apple-header {{
            display: flex;
            align-items: center;
            margin-bottom: 90px; /* Increased from 70px for better placement */
            /* Entrance Logic */
            opacity: 0;
            animation: heroEntrance 1s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
            animation-delay: 3.6s; /* Wait for Splash */
        }}
        
        .logo-mark {{
            width: 80px; /* Slightly larger logo to match title */
            height: 80px;
            border-radius: 20px;
            box-shadow: 0 0 40px rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .header-text {{
            margin-left: 28px;
        }}
        
        .header-text h1 {{
            font-size: 4.5rem; /* Increased from 3.5rem for Executive Look */
            font-weight: 700;
            letter-spacing: -0.03em;
            margin: 0;
            background: linear-gradient(135deg, #ffffff 0%, #8b8b99 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        
        .header-text p {{
            color: #86868b;
            font-size: 1.1rem;
            margin: 6px 0 0 0;
            font-weight: 400;
            letter-spacing: 0.5px;
        }}

        /* --- HOLOGRAPHIC GLASS CARDS --- */
        
        /* 1. Base Container */
        div.stButton > button {{
            all: unset; 
            width: 100% !important; /* Force full width */
            height: 200px !important; /* Fixed height for perfect symmetry */
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            padding: 30px; /* Reduced padding to prevent content crowding */
            box-sizing: border-box;
            
            /* Transparent base allows ::before spinner to show through if needed, 
               but we rely on positioning */
            background: transparent;
            border: none;
            border-radius: 24px; /* Sharper, more professional radius */
            
            /* Stacking Context */
            position: relative;
            overflow: hidden; /* Clips the spinning lights at the corners */
            
            /* Motion Entrance */
            opacity: 0; 
            animation: cardFloatUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }}
        
        /* Staggered Entry for Cards */
        div.stButton:nth-of-type(1) > button {{ animation-delay: 3.7s; }}
        div.stButton:nth-of-type(2) > button {{ animation-delay: 3.8s; }}
        div.stButton:nth-of-type(3) > button {{ animation-delay: 3.9s; }}
        div.stButton:nth-of-type(4) > button {{ animation-delay: 4.0s; }}
        div.stButton:nth-of-type(5) > button {{ animation-delay: 4.1s; }}

        /* 2. THE ROTATING LIGHTS (ON HOVER) - Bottom Layer (Layer 0) */
        div.stButton > button::before {{
            content: "";
            position: absolute;
            top: 50%; left: 50%;
            width: 200%; height: 200%;
            /* The Spinning Conic Gradient */
            background: conic-gradient(from 0deg, transparent 0%, #007aff 20%, #ffffff 40%, transparent 60%);
            transform: translate(-50%, -50%);
            z-index: 0; /* Behind the glass body */
            opacity: 0; /* Hidden by default */
            transition: opacity 0.5s ease;
            pointer-events: none;
        }}
        
        /* Hover Interaction: Ignite the lights */
        div.stButton > button:hover::before {{
            opacity: 1;
            animation: rotateBorder 3s linear infinite;
        }}

        /* 3. THE GLASS BODY & AUTOMATIC SHEEN - Middle Layer (Layer 1) */
        div.stButton > button::after {{
            content: "";
            position: absolute;
            /* Inset by 2px to allow the Rotating Lights (Layer 0) to act as a border */
            inset: 2px; 
            border-radius: 22px; /* Matches button radius minus border width */
            background: rgba(20, 20, 30, 0.6); /* Deep Glass */
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.5);
            z-index: 1;
            
            /* THE PERIODIC SHEEN (Background Image Gradient) */
            background-image: linear-gradient(
                120deg, 
                transparent 30%, 
                rgba(255, 255, 255, 0.1) 45%, 
                rgba(255, 255, 255, 0.2) 50%, 
                rgba(255, 255, 255, 0.1) 55%, 
                transparent 70%
            );
            background-size: 250% 100%;
            background-position: 200% 0; /* Start off-screen right */
            
            /* Continuous "Living" Animation */
            animation: periodicSheen 6s ease-in-out infinite;
        }}

        /* 4. TEXT CONTENT - Top Layer (Layer 2) */
        div.stButton > button p {{
            position: relative;
            z-index: 2;
            color: #f5f5f7;
            font-size: 1.4rem;
            font-weight: 600;
            letter-spacing: 0.3px;
            margin: 0;
            text-align: left;
            width: 100%;
            line-height: 1.4;
            pointer-events: none;
        }}
        
        /* Hover State for Body (Scale Up) */
        div.stButton > button:hover {{
            transform: translateY(-8px) scale(1.02);
            /* No background change here, we rely on ::after */
        }}
        
        div.stButton > button:hover::after {{
             background-color: rgba(30, 30, 45, 0.7); /* Slightly lighter glass on hover */
        }}

        /* ANIMATIONS */
        @keyframes heroEntrance {{
            from {{ opacity: 0; transform: translateY(20px); filter: blur(10px); }}
            to {{ opacity: 1; transform: translateY(0); filter: blur(0px); }}
        }}
        
        @keyframes cardFloatUp {{
            from {{ opacity: 0; transform: translateY(50px) scale(0.95); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}
        
        @keyframes rotateBorder {{
            from {{ transform: translate(-50%, -50%) rotate(0deg); }}
            to {{ transform: translate(-50%, -50%) rotate(360deg); }}
        }}

        @keyframes periodicSheen {{
            0% {{ background-position: 200% 0; }} /* Off screen right */
            20% {{ background-position: -100% 0; }} /* Sweep to left */
            100% {{ background-position: -100% 0; }} /* Wait (Pause) */
        }}

    </style>
""", unsafe_allow_html=True)

# --- 6. RENDER HEADER ---
logo_img = f'<img src="data:image/jpg;base64,{logo_b64}" class="logo-mark">' if logo_b64 else ""

# OPTIONAL HARDENING: prevent silent "white screen" on render-time errors
try:
    st.markdown(f"""
        <div class="apple-header">
            {logo_img}
            <div class="header-text">
                <h1>HayCash ToolBox</h1>
                <p>Secure Intelligence Protocol</p>
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
            # Card Layout: Icon on top, Name below
            label_text = f"{icon}  \n\n{name}"

            # The Button IS the Card
            if st.button(label_text, key=f"app_{a.get('id')}"):
                target = PAGE_BY_ID.get(a.get("id"))
                if target:
                    safe_navigate(target, name)
                else:
                    st.error(f"Module '{name}' not linked.")

            st.write("")  # Layout spacer
            st.write("")

except Exception as e:
    st.error("App crashed while rendering.")
    st.exception(e)
