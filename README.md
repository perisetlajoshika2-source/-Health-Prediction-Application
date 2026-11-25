# Health Prediction Application

Streamlit CRUD web application for patient blood-test records and AI-assisted screening remarks. Records persist in `health_records.json` using Python standard-library JSON storage.

## Navigation

- Dashboard: overview of patient and screening totals
- Register Patient: add a patient and generate remarks
- Health Assessment: review a selected patient's blood-test screening note
- Manage Patients: edit or delete records
- Patient History: search records by name, email, or patient ID

## Run in VS Code

1. Open VS Code.
2. Select **File > Open Folder** and open `C:\Users\naren\health-prediction-app`.
3. Open a terminal in VS Code with **Terminal > New Terminal**.
4. Move to the project folder:

```powershell
cd C:\Users\naren\health-prediction-app
```

5. Create a virtual environment if `.venv` does not already exist:

```powershell
python -m venv .venv
```

6. Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If Windows shows an execution-policy error, allow scripts only for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

7. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

8. Start the application on port 8502:

```powershell
python -m streamlit run app.py --server.port 8502
```

9. Open http://localhost:8502.

To stop the application, press `Ctrl+C` in the VS Code terminal.

## External AI API

Copy `.env.example` to `.env` and set `AI_API_KEY`. The application uses an OpenAI-compatible chat-completions endpoint. Do not commit `.env` or any API key.

When no key is configured, the application uses a clearly identified local screening fallback so the UI remains usable for demonstration.

## Validation demo

John Hunter is rejected for an invalid email. Peter Larry is rejected because `31.11.2001` is not a real date. Kris Wu is rejected for a future birth date and invalid email. The remaining records can be created normally, and the remarks field is generated on create or update.
