# Streamlit version (Python)

## Run
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Notes
- Logic translated from the original `app.R` (Shiny) to Python (`factoraje_logic.py`).
- Uses the same endpoints and filtering rules:
  - Only received invoices (isIssuer=false)
  - Only TipoDeComprobante == I
  - receptor_rfc == target RFC and emisor_rfc != target RFC
- Excel export creates 1 sheet per RFC with grouped headers per interval.
