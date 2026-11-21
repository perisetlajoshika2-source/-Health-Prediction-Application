# Health Prediction Application

Streamlit CRUD web application for patient blood-test records and AI-assisted screening remarks. Records persist in `health_records.json` using Python standard-library JSON storage.

## Navigation

- Dashboard: overview of patient and screening totals
- Register Patient: add a patient and generate remarks
- Health Assessment: review a selected patient's blood-test screening note
- Manage Patients: edit or delete records
- Patient History: search records by name, email, or patient ID

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit, normally http://localhost:8501.

## External AI API

Copy `.env.example` to `.env` and set `AI_API_KEY`. The application uses an OpenAI-compatible chat-completions endpoint. Do not commit `.env` or any API key.

When no key is configured, the application uses a clearly identified local screening fallback so the UI remains usable for demonstration.

## Validation demo

John Hunter is rejected for an invalid email. Peter Larry is rejected because `31.11.2001` is not a real date. Kris Wu is rejected for a future birth date and invalid email. The remaining records can be created normally, and the remarks field is generated on create or update.
