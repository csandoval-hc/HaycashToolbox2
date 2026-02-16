# analisis_leads_streamlit

## Run (Windows PowerShell)

```powershell
cd "C:\Users\CarlosSandovalCohen\Downloads\analisis_leads_streamlit"
pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Files expected
- `data/snapshot.csv` (input snapshot)
- `data/reviewed_leads_app.csv` (created/updated by the app)
- Optional blocklist: `www/cat_credit_id_rfc.csv` (column RFC)

