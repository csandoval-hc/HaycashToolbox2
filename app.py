import base64
from pathlib import Path
import streamlit as st
import yaml
from simple_auth import require_shared_password

# --- 1. CONFIGURATION: PREPARE THE CANVAS ---
st.set_page_config(
    page_title="HayCash Terminal",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

require_shared_password()

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

# --- 2. ASSET LOADING ---
def b64(path: Path) -> str:
    if not path.exists(): return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def load_registry():
    cfg_path = ROOT / "apps.yaml"
    if not cfg_path.exists(): return []
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return cfg.get("apps", [])

# --- 3. NAVIGATION REGISTRY ---
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

# --- 4. THE "AMEX" STYLE ENGINE ---
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

        /* HIDE STREAMLIT CHROME */
        [data-testid="stSidebarNav"], 
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"] {{
            display: none !important;
        }}

        /* --- SIDEBAR: THE COMMAND TOWER --- */
        section[data-testid="stSidebar"] {{
            background-color: #06080C !important;
            border-right: 1px solid #1E232F;
            width: 300px !important;
            padding-top: 0 !important;
        }}
        
        /* LOGO CONTAINER */
        .sidebar-logo-container {{
            padding: 30px 20px;
            text-align: center;
            border-bottom: 1px solid #1E232F;
            background: #06080C;
            margin-bottom: 20px;
        }}
        .sidebar-logo {{
            width: 100%;
            max-width: 220px; /* Big and Bold */
            height: auto;
            filter: drop-shadow(0 0 10px rgba(255,255,255,0.05));
        }}

        /* SIDEBAR LINKS */
        .nav-header {{
            color: #586578;
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 0 25px;
            margin-bottom: 10px;
        }}
        
        div.stButton > button {{
            background: transparent !important;
            border: 1px solid transparent !important;
            color: #94A3B8 !important;
            text-align: left !important;
            padding: 12px 25px !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease-in-out;
            border-radius: 0 !important;
            margin: 0 !important;
            width: 100%;
            display: flex;
            align-items: center;
        }}
        
        /* HOVER STATE FOR SIDEBAR */
        div.stButton > button:hover {{
            background: #11151E !important;
            color: #FFFFFF !important;
            border-left: 3px solid #FFBA00 !important;
            padding-left: 22px !important; /* Compensate for border */
        }}

        /* --- HERO SECTION --- */
        .block-container {{
            padding-top: 2rem !important;
            max-width: 1600px !important;
        }}
        
        .dashboard-header {{
            margin-bottom: 60px;
        }}
        .welcome-eyebrow {{
            color: #FFBA00;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .welcome-title {{
            color: #FFFFFF;
            font-size: 3.5rem;
            font-weight: 800;
            line-height: 1.1;
            letter-spacing: -0.02em;
        }}
        .welcome-subtitle {{
            color: #64748B;
            font-size: 1.2rem;
            font-weight: 400;
            margin-top: 15px;
            max-width: 600px;
        }}

        /* --- THE CARD GRID --- */
        .grid-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
        }}

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
            overflow: hidden;
        }}

        /* PREMIUM HOVER GLOW */
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
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.01em;
        }}

        .fin-card-desc {{
            color: #64748B;
            font-size: 0.9rem;
            line-height: 1.6;
            margin-bottom: 30px;
            flex-grow: 1;
        }}

        /* BUTTON OVERRIDES FOR GRID */
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
            top: 2rem;
            right: 2rem;
            color: #64748B;
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
        }}

    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR CONSTRUCTION ---
with st.sidebar:
    # 5.1 THE LOGO (Large & Prominent)
    if logo_b64:
        st.markdown(f"""
            <div class="sidebar-logo-container">
                <img src="data:image/jpg;base64,{logo_b64}" class="sidebar-logo">
            </div>
        """, unsafe_allow_html=True)
    
    # 5.2 NAVIGATION LINKS
    st.markdown('<div class="nav-header">PLATAFORMA</div>', unsafe_allow_html=True)
    
    # Home is active by default logic visually (handled by Streamlit routing)
    st.button("🏠  Dashboard", key="nav_home", disabled=True) 

    st.markdown('<div class="nav-header" style="margin-top: 20px;">HERRAMIENTAS</div>', unsafe_allow_html=True)

    # Render Nav Items
    for app_id, page in PAGE_BY_ID.items():
        # Get clean name
        raw_name = next((a.get("name") for a in apps if a.get("id") == app_id), app_id)
        
        # Assign premium icons
        icon = "●"
        if "CSF" in raw_name: icon = "🧾"
        elif "BBVA" in raw_name: icon = "🏦"
        elif "Leads" in raw_name: icon = "📊"
        elif "Factoraje" in raw_name: icon = "💳"
        elif "Edocat" in raw_name: icon = "📄"
        elif "Consejo" in raw_name: icon = "📈"
        elif "Contrato" in raw_name: icon = "📝"
        
        # Sidebar Button
        if st.button(f"{icon}  {raw_name}", key=f"side_{app_id}"):
            st.switch_page(page)

    # 5.3 BOTTOM META
    st.markdown("""
        <div style="position: fixed; bottom: 20px; left: 20px; color: #334155; font-size: 0.7rem;">
            HayCash Secure Terminal<br>v2.4.0 • Encrypted
        </div>
    """, unsafe_allow_html=True)


# --- 6. MAIN DASHBOARD CONTENT ---

# 6.1 SYSTEM STATUS (Top Right)
st.markdown("""
    <div class="system-status">
        <span class="status-dot"></span> SYSTEM OPERATIONAL
    </div>
""", unsafe_allow_html=True)

# 6.2 HERO HEADER
st.markdown("""
    <div class="dashboard-header">
        <div class="welcome-eyebrow">HAYCASH TOOLBOX</div>
        <div class="welcome-title">Centro de Control</div>
        <div class="welcome-subtitle">
            Seleccione un módulo operativo para comenzar. Todas las conexiones son seguras y monitoreadas.
        </div>
    </div>
""", unsafe_allow_html=True)

# 6.3 APP GRID (The "Vault" Look)
cols = st.columns(3)

for i, a in enumerate(apps):
    col = cols[i % 3]
    
    name = a.get("name", "Module")
    # Icon Selection
    icon = "⚡"
    if "CSF" in name: icon = "🧾"
    elif "BBVA" in name: icon = "🏦"
    elif "Leads" in name: icon = "📊"
    elif "Factoraje" in name: icon = "💳"
    elif "Edocat" in name: icon = "📄"
    elif "Consejo" in name: icon = "📈"
    elif "Contrato" in name: icon = "📝"

    with col:
        # We render the card visuals in HTML
        st.markdown(f"""
            <div class="fin-card">
                <div class="icon-box">{icon}</div>
                <div>
                    <div class="fin-card-title">{name}</div>
                    <div class="fin-card-desc">Acceso autorizado al módulo de {name.lower()}. Procesamiento de datos y reportes en tiempo real.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # The Action Button (Hidden visually but clickable, or styled to match)
        # To make it feel premium, we use a full-width button right below the card visual
        # In this layout, placing the button cleanly is key.
        if st.button(f"INICIAR {name.upper()}", key=f"dash_{a.get('id')}", use_container_width=True):
            target = PAGE_BY_ID.get(a.get("id"))
            if target:
                st.switch_page(target)
        
        # Spacer
        st.markdown("<div style='margin-bottom: 30px'></div>", unsafe_allow_html=True)
