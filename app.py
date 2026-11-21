import os
import re
import json
import csv
import io
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "health_records.json")


def init_storage():
    if not os.path.exists(DATA_FILE):
        save_patients([])


def load_patients():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_patients(patients):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(patients, file, indent=2, ensure_ascii=False)


def parse_date(value):
    value = (value or "").strip()
    for date_format in ("%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    raise ValueError("Invalid date of birth. Enter it in dd/mm/yyyy format, for example 28/01/1960.")


def validate_patient(full_name, date_of_birth, email, glucose, haemoglobin, cholesterol):
    errors = {}
    parsed_date = None

    if len(full_name.strip()) < 2:
        errors["full_name"] = "Full name must contain at least 2 characters."

    try:
        parsed_date = parse_date(date_of_birth)
        if parsed_date > datetime.now().date():
            errors["date_of_birth"] = "Date of birth cannot be a future date."
    except ValueError as error:
        errors["date_of_birth"] = str(error)

    if not re.match(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$", email.strip()):
        errors["email"] = "Invalid email address. Enter a valid email, such as name@example.com."

    blood_values = {}
    for field, value in (
        ("glucose", glucose),
        ("haemoglobin", haemoglobin),
        ("cholesterol", cholesterol),
    ):
        try:
            numeric_value = float(value)
            if numeric_value < 0:
                raise ValueError
            blood_values[field] = numeric_value
        except (TypeError, ValueError):
            errors[field] = f"{field.capitalize()} must be a positive numeric value."

    return errors, parsed_date if "date_of_birth" not in errors else None, blood_values


def local_health_assessment(glucose, haemoglobin, cholesterol):
    findings = []
    if glucose >= 126:
        findings.append("high glucose may indicate diabetes risk")
    elif glucose >= 100:
        findings.append("borderline high glucose")

    if haemoglobin < 13:
        findings.append("low haemoglobin may indicate anaemia risk")
    elif haemoglobin > 17.5:
        findings.append("unusually high haemoglobin")

    if cholesterol >= 240:
        findings.append("high cholesterol")
    elif cholesterol >= 200:
        findings.append("borderline high cholesterol")

    if not findings:
        return "Values appear within common screening ranges. Routine medical follow-up is advised."
    return "Screening note: " + "; ".join(findings) + ". Confirm with a qualified healthcare professional."


def call_external_ai(glucose, haemoglobin, cholesterol):
    api_url = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_API_MODEL", "gpt-4o-mini")

    if not api_key:
        return (
            local_health_assessment(glucose, haemoglobin, cholesterol),
            "Local screening fallback (set AI_API_KEY to enable external AI)",
        )

    prompt = (
        "Act as a conservative health-screening assistant. "
        "Provide a short possible-risk note for these blood test values. "
        "Do not diagnose or prescribe. "
        f"Glucose: {glucose} mg/dL; "
        f"Haemoglobin: {haemoglobin} g/dL; "
        f"Cholesterol: {cholesterol} mg/dL."
    )

    try:
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You provide brief, cautious medical screening notes."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        remarks = payload["choices"][0]["message"]["content"].strip()
        return remarks, f"External AI ({model})"
    except (requests.RequestException, KeyError, IndexError, ValueError) as error:
        fallback = local_health_assessment(glucose, haemoglobin, cholesterol)
        return fallback, f"Local fallback because external API failed: {type(error).__name__}"


def list_patients():
    return sorted(load_patients(), key=lambda patient: patient["id"])


def create_patient(full_name, date_of_birth, email, glucose, haemoglobin, cholesterol, remarks):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    patients = load_patients()
    patient_id = max((patient["id"] for patient in patients), default=0) + 1
    patients.append(
        {
            "id": patient_id,
            "full_name": full_name,
            "date_of_birth": date_of_birth,
            "email": email,
            "glucose": glucose,
            "haemoglobin": haemoglobin,
            "cholesterol": cholesterol,
            "remarks": remarks,
            "created_at": now,
            "updated_at": now,
        }
    )
    save_patients(patients)
    return patient_id


def update_patient(patient_id, full_name, date_of_birth, email, glucose, haemoglobin, cholesterol, remarks):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    patients = load_patients()
    for patient in patients:
        if patient["id"] == patient_id:
            patient.update(
                {
                    "full_name": full_name,
                    "date_of_birth": date_of_birth,
                    "email": email,
                    "glucose": glucose,
                    "haemoglobin": haemoglobin,
                    "cholesterol": cholesterol,
                    "remarks": remarks,
                    "updated_at": now,
                }
            )
            break
    save_patients(patients)


def delete_patient(patient_id):
    patients = load_patients()
    save_patients([patient for patient in patients if patient["id"] != patient_id])


init_storage()
st.set_page_config(page_title="Health Prediction", page_icon="✚", layout="wide")

st.markdown(
    """
    <style>
    :root { --navy:#102a43; --teal:#087f8c; --cyan:#20b8cd; --ink:#243b53; }
    .stApp {
      background: radial-gradient(circle at 88% 8%, rgba(32,184,205,.14), transparent 24rem),
                  radial-gradient(circle at 12% 78%, rgba(16,42,67,.05), transparent 18rem),
                  linear-gradient(145deg,#f8fbff 0%,#edf8f7 55%,#eef4ff 100%);
      color:var(--ink);
    }
    [data-testid="stAppViewContainer"]::after {
      content:"✚";
      position:fixed;
      right:-38px;
      bottom:-82px;
      z-index:-1;
      color:rgba(8,127,140,.045);
      font-family:Georgia,serif;
      font-size:310px;
      font-weight:900;
      line-height:1;
      transform:rotate(-8deg);
      pointer-events:none;
    }
    [data-testid="stAppViewContainer"]::before {
      content:"";
      position:fixed;
      inset:0;
      z-index:-1;
      pointer-events:none;
      opacity:.48;
      background-image:
        linear-gradient(118deg, transparent 0 68%, rgba(32,184,205,.035) 68% 69%, transparent 69%),
        radial-gradient(circle at 50% 50%, rgba(8,127,140,.045) 0 2px, transparent 3px);
      background-size:auto,34px 34px;
    }
    .medical-watermark {
      position:fixed;
      inset:0;
      z-index:-1;
      pointer-events:none;
      overflow:hidden;
      color:rgba(8,127,140,.065);
      font-family:Georgia,"Segoe UI Symbol",serif;
      font-weight:700;
    }
    .medical-watermark span {
      position:absolute;
    }
    .medical-watermark .heart { left:14%; top:20%; font-size:72px; transform:rotate(-12deg); }
    .medical-watermark .pulse { right:18%; top:24%; font-size:88px; transform:rotate(8deg); }
    .medical-watermark .staff { left:22%; bottom:9%; font-size:96px; transform:rotate(5deg); }
    [data-testid="stSidebar"] {
      background:linear-gradient(180deg,#102a43 0%,#173f5f 100%);
      border-right:1px solid rgba(255,255,255,.08);
    }
    [data-testid="stSidebar"] * { color:#eaf8f7; }
    [data-testid="stSidebarNav"] { display:none; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
      border-radius:10px;
      padding:8px 10px;
      margin-bottom:5px;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
      background:rgba(32,184,205,.14);
    }
    .sidebar-brand {
      display:flex;
      align-items:center;
      gap:12px;
      margin:8px 0 4px;
    }
    .sidebar-brand-icon {
      display:grid;
      place-items:center;
      width:48px;
      height:48px;
      border-radius:14px;
      background:linear-gradient(135deg,#20b8cd,#56d8c8);
      color:#102a43;
      font-size:30px;
      font-weight:900;
      box-shadow:0 10px 24px rgba(32,184,205,.22);
    }
    .sidebar-brand-name {
      color:#ffffff;
      font-size:27px;
      font-weight:800;
      letter-spacing:-.03em;
      line-height:1;
    }
    .block-container { max-width:1180px; padding-top:1.25rem; }
    [data-testid="stMetric"], [data-testid="stForm"], [data-testid="stContainer"] {
      border:1px solid #d7e8ec;
      border-radius:16px;
      background:rgba(255,255,255,.94);
      box-shadow:0 10px 28px rgba(16,42,67,.07);
    }
    [data-testid="stMetric"] { padding:14px 16px; }
    [data-testid="stForm"] { padding:20px; }
    [data-testid="stFormSubmitButton"] button {
      border:0; background:linear-gradient(135deg,#087f8c,#20b8cd); color:white;
    }
    [data-testid="stButton"] button { border-radius:10px; font-weight:700; }
    .patient-fab {
      position:fixed;
      right:28px;
      bottom:28px;
      z-index:999;
      display:grid;
      place-items:center;
      width:62px;
      height:62px;
      border-radius:50%;
      background:linear-gradient(135deg,#087f8c,#20b8cd);
      color:#ffffff !important;
      text-decoration:none;
      font-size:38px;
      font-weight:300;
      line-height:1;
      box-shadow:0 14px 34px rgba(8,127,140,.38);
      border:4px solid rgba(255,255,255,.92);
      transition:.2s ease;
    }
    .patient-fab:hover {
      transform:translateY(-3px);
      box-shadow:0 18px 40px rgba(8,127,140,.48);
    }
    .hero {
      display:flex; align-items:center; gap:16px; padding:22px;
      border:1px solid #ccebe6; border-radius:18px;
      background:linear-gradient(120deg,rgba(255,255,255,.96),rgba(237,250,248,.94));
      box-shadow:0 14px 34px rgba(16,42,67,.08); margin-bottom:18px;
    }
    .hero-icon {
      display:grid; place-items:center; width:54px; height:54px; border-radius:16px;
      background:linear-gradient(135deg,#087f8c,#20b8cd); color:white;
      font-size:28px; box-shadow:0 10px 22px rgba(8,127,140,.22);
    }
    .hero h1 { margin:0; color:var(--navy); font-size:2rem; }
    .hero p { margin:5px 0 0; color:#627d98; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-icon">✚</div>'
        '<div class="sidebar-brand-name">HealthCare</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Patient management workspace")
    page_param = st.query_params.get("page")
    page_names = [
        "Dashboard",
        "Register Patient",
        "Health Assessment",
        "Manage Patients",
        "Patient History",
    ]
    param_indexes = {
        "dashboard": 0,
        "register": 1,
        "assessment": 2,
        "manage": 3,
        "history": 4,
    }
    default_index = param_indexes.get(str(page_param).lower(), 0)
    page = st.radio(
        "Navigation",
        page_names,
        index=default_index,
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Records: " + str(len(list_patients())))

st.markdown(
    '<a class="patient-fab" href="?page=register" aria-label="Register a new patient" title="Register Patient">+</a>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="medical-watermark">'
    '<span class="heart">♥</span>'
    '<span class="pulse">⌁</span>'
    '<span class="staff">⚕</span>'
    '</div>',
    unsafe_allow_html=True,
)

def hero(title, subtitle):
    st.markdown(
        f'<section class="hero"><div class="hero-icon">✚</div>'
        f'<div><h1>{title}</h1><p>{subtitle}</p></div></section>',
        unsafe_allow_html=True,
    )

def patient_form(editing=None, key_prefix="new"):
    with st.form(f"patient-form-{key_prefix}", clear_on_submit=(editing is None)):
        c1, c2, c3 = st.columns(3)
        with c1:
            full_name = st.text_input("Full Name", value=editing["full_name"] if editing else "", key=f"name-{key_prefix}")
            glucose = st.number_input("Glucose", min_value=0.0, step=0.1, value=float(editing["glucose"]) if editing else 0.0, key=f"glucose-{key_prefix}")
        with c2:
            dob = st.text_input("Date of Birth (dd/mm/yyyy)", value=editing["date_of_birth"] if editing else "", placeholder="28/01/1960", key=f"dob-{key_prefix}")
            haemoglobin = st.number_input("Haemoglobin", min_value=0.0, step=0.1, value=float(editing["haemoglobin"]) if editing else 0.0, key=f"hgb-{key_prefix}")
        with c3:
            email = st.text_input("Email Address", value=editing["email"] if editing else "", key=f"email-{key_prefix}")
            cholesterol = st.number_input("Cholesterol", min_value=0.0, step=0.1, value=float(editing["cholesterol"]) if editing else 0.0, key=f"cholesterol-{key_prefix}")
        submitted = st.form_submit_button("Update Patient" if editing else "Save Patient", width="stretch")

    if submitted:
        errors, parsed_date, blood_values = validate_patient(full_name, dob, email, glucose, haemoglobin, cholesterol)
        if errors:
            for message in errors.values():
                st.error(message)
            return
        remarks, api_source = call_external_ai(blood_values["glucose"], blood_values["haemoglobin"], blood_values["cholesterol"])
        if editing:
            update_patient(editing["id"], full_name.strip(), parsed_date.strftime("%d/%m/%Y"), email.strip(), blood_values["glucose"], blood_values["haemoglobin"], blood_values["cholesterol"], remarks)
            st.session_state.editing_id = None
            st.success(f"Patient updated successfully. {api_source}")
        else:
            create_patient(full_name.strip(), parsed_date.strftime("%d/%m/%Y"), email.strip(), blood_values["glucose"], blood_values["haemoglobin"], blood_values["cholesterol"], remarks)
            st.success(f"Patient registered successfully. {api_source}")
        st.rerun()

if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

patients = list_patients()

if page == "Dashboard":
    hero("Health Dashboard", "Overview of patient records and screening activity")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Patients", len(patients))
    c2.metric("Glucose Alerts", sum(p["glucose"] >= 100 for p in patients))
    c3.metric("Cholesterol Alerts", sum(p["cholesterol"] >= 200 for p in patients))

    title_col, filter_col, download_col = st.columns([3.2, 1.2, 1.2])
    with title_col:
        st.subheader("Recent Records")
    with filter_col:
        show_records = st.toggle("Show list", value=True)
    with download_col:
        output = io.StringIO()
        fieldnames = [
            "id", "full_name", "date_of_birth", "email", "glucose",
            "haemoglobin", "cholesterol", "remarks",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(patients)
        st.download_button(
            "⬇ Download All",
            data=output.getvalue(),
            file_name="patient_records.csv",
            mime="text/csv",
            width="stretch",
        )

    if not patients:
        st.info("No patient records have been registered.")
    elif show_records:
        filter_col1, filter_col2, filter_col3 = st.columns([2, 1.2, 1.2])
        with filter_col1:
            record_search = st.text_input(
                "Filter recent records",
                placeholder="Search name, email, or ID",
                key="recent-record-filter",
            )
        with filter_col2:
            glucose_filter = st.selectbox(
                "Glucose",
                ["All", "Normal / Below 100", "Elevated 100+"],
                key="recent-glucose-filter",
            )
        with filter_col3:
            cholesterol_filter = st.selectbox(
                "Cholesterol",
                ["All", "Normal / Below 200", "Elevated 200+"],
                key="recent-cholesterol-filter",
            )

        filtered_patients = list(reversed(patients))
        if record_search.strip():
            query = record_search.strip().lower()
            filtered_patients = [
                p for p in filtered_patients
                if query in p["full_name"].lower()
                or query in p["email"].lower()
                or query in str(p["id"])
            ]
        if glucose_filter == "Normal / Below 100":
            filtered_patients = [p for p in filtered_patients if p["glucose"] < 100]
        elif glucose_filter == "Elevated 100+":
            filtered_patients = [p for p in filtered_patients if p["glucose"] >= 100]
        if cholesterol_filter == "Normal / Below 200":
            filtered_patients = [p for p in filtered_patients if p["cholesterol"] < 200]
        elif cholesterol_filter == "Elevated 200+":
            filtered_patients = [p for p in filtered_patients if p["cholesterol"] >= 200]

        records_per_page = 20
        total_pages = max(1, (len(filtered_patients) + records_per_page - 1) // records_per_page)
        if "recent_page" not in st.session_state:
            st.session_state.recent_page = 1
        st.session_state.recent_page = min(st.session_state.recent_page, total_pages)

        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col1:
            if st.button("‹ Previous", disabled=st.session_state.recent_page <= 1, width="stretch"):
                st.session_state.recent_page -= 1
                st.rerun()
        with page_col2:
            st.markdown(
                f"<p style='text-align:center;margin:8px 0;'>"
                f"{len(filtered_patients)} records · Page {st.session_state.recent_page} of {total_pages}"
                f"</p>",
                unsafe_allow_html=True,
            )
        with page_col3:
            if st.button("Next ›", disabled=st.session_state.recent_page >= total_pages, width="stretch"):
                st.session_state.recent_page += 1
                st.rerun()

        start = (st.session_state.recent_page - 1) * records_per_page
        recent_patients = filtered_patients[start:start + records_per_page]
        table_rows = [
            {
                "ID": p["id"],
                "Patient": p["full_name"],
                "Date of Birth": p["date_of_birth"],
                "Email": p["email"],
                "Glucose": f"{p['glucose']} mg/dL",
                "Haemoglobin": f"{p['haemoglobin']} g/dL",
                "Cholesterol": f"{p['cholesterol']} mg/dL",
            }
            for p in recent_patients
        ]
        if not table_rows:
            st.info("No recent records match the selected filters.")
        else:
            st.dataframe(
                table_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn(width="small"),
                    "Patient": st.column_config.TextColumn(width="medium"),
                    "Email": st.column_config.TextColumn(width="medium"),
                },
            )

elif page == "Register Patient":
    hero("Register Patient", "Add a new patient and generate an initial screening remark")
    patient_form()

elif page == "Health Assessment":
    hero("Health Assessment", "Review a patient's blood-test screening risk")
    if not patients:
        st.info("Register a patient before running an assessment.")
    else:
        choices = {f"#{p['id']} — {p['full_name']}": p["id"] for p in patients}
        selected = st.selectbox("Select Patient", list(choices))
        patient = next(p for p in patients if p["id"] == choices[selected])
        c1, c2, c3 = st.columns(3)
        c1.metric("Glucose", f"{patient['glucose']} mg/dL")
        c2.metric("Haemoglobin", f"{patient['haemoglobin']} g/dL")
        c3.metric("Cholesterol", f"{patient['cholesterol']} mg/dL")
        st.info(patient["remarks"])

elif page == "Manage Patients":
    hero("Manage Patients", "Edit or delete patient records")
    editing = next((p for p in patients if p["id"] == st.session_state.editing_id), None)
    if editing:
        st.subheader(f"Editing #{editing['id']} — {editing['full_name']}")
        patient_form(editing, f"edit-{editing['id']}")
        if st.button("✕ Cancel Edit"):
            st.session_state.editing_id = None
            st.rerun()
    st.subheader("All Patients")
    if not patients:
        st.info("No patient records have been registered.")
    else:
        for patient in patients:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2.4, 2.2, 1.2])
                with c1:
                    st.markdown(f"**#{patient['id']} — {patient['full_name']}**")
                    st.caption(f"{patient['email']} · DOB {patient['date_of_birth']}")
                with c2:
                    st.markdown(f"Glucose {patient['glucose']} · Hb {patient['haemoglobin']} · Cholesterol {patient['cholesterol']}")
                    st.caption(patient["remarks"])
                with c3:
                    if st.button("✎ Edit", key=f"edit-{patient['id']}", width="stretch"):
                        st.session_state.editing_id = patient["id"]
                        st.rerun()
                    if st.button("🗑 Delete", key=f"delete-{patient['id']}", width="stretch"):
                        delete_patient(patient["id"])
                        st.success(f"Patient #{patient['id']} deleted.")
                        st.rerun()

elif page == "Patient History":
    hero("Patient History", "Search and review complete patient records")
    search = st.text_input("🔎 Search by name, email, or patient ID")
    filtered = patients
    if search.strip():
        query = search.strip().lower()
        filtered = [
            p for p in patients
            if query in p["full_name"].lower()
            or query in p["email"].lower()
            or query in str(p["id"])
        ]
    st.caption(f"{len(filtered)} matching record(s)")
    if not filtered:
        st.info("No patient history matches your search.")
    else:
        for patient in filtered:
            with st.expander(f"#{patient['id']} — {patient['full_name']}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Email:**", patient["email"])
                    st.write("**Date of Birth:**", patient["date_of_birth"])
                    st.write("**Created:**", patient["created_at"])
                with c2:
                    st.write("**Glucose:**", f"{patient['glucose']} mg/dL")
                    st.write("**Haemoglobin:**", f"{patient['haemoglobin']} g/dL")
                    st.write("**Cholesterol:**", f"{patient['cholesterol']} mg/dL")
                st.write("**AI Screening Remark:**")
                st.caption(patient["remarks"])
