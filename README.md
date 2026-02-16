# Haycash Toolbox (Streamlit)

This repo is a Streamlit "launcher" (Toolbox) that displays your apps as neon cards.

## Run locally
1) Create/activate a virtualenv
2) Install deps:
   pip install -r requirements.txt
3) Start:
   streamlit run app.py

## Add / remove apps
Edit `apps.yaml`. Each entry controls one card:
- name: MUST be exactly the app name you want displayed
- url: link to the Streamlit app
- icon: path to an svg icon (optional)

## Assets
- `assets/haycash_logo.jpg` (your Haycash logo)
- `assets/bg.jpg` (background image)

Replace `assets/bg.jpg` if you want a different star background.
