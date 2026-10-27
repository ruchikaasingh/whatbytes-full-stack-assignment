# Healthcare Backend (Django + DRF + PostgreSQL + JWT)

REST API to register/login users and manage patients, doctors and patient-doctor assignments.

## Project structure

```
healthcare_backend/
├── manage.py
├── requirements.txt
├── .env.example          # copy to .env and fill in
├── config/               # settings, root urls, custom exception handler
├── accounts/             # register + login (JWT)
├── patients/             # Patient model + CRUD
├── doctors/              # Doctor model + CRUD
└── mappings/             # PatientDoctorMapping + API tests
```

## Setup

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# create the database (psql)
#   CREATE DATABASE healthcare_db;

cp .env.example .env        # then edit SECRET_KEY and DB_* values
python manage.py migrate
python manage.py runserver
```

All secrets (SECRET_KEY, DB credentials, DEBUG, ALLOWED_HOSTS) come from environment variables / `.env`.
`.env` is git-ignored; never commit it.

Run the tests (they need the PostgreSQL user to be allowed to create a test database):

```bash
python manage.py test
```

## Endpoints

Send the token on every request except register/login: `Authorization: Bearer <access_token>`

| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/register/` | `{name, email, password}` |
| POST | `/api/auth/login/` | `{email, password}` -> `{access, refresh, user}` |
| POST | `/api/patients/` | Add a patient |
| GET | `/api/patients/` | Patients created by the logged-in user |
| GET/PUT/DELETE | `/api/patients/<id>/` | Own patient only (others get 404) |
| POST | `/api/doctors/` | Add a doctor |
| GET | `/api/doctors/` | All doctors |
| GET | `/api/doctors/<id>/` | One doctor |
| PUT/DELETE | `/api/doctors/<id>/` | Only the user who created the doctor (others get 403) |
| POST | `/api/mappings/` | `{patient, doctor}` - assign a doctor to one of your patients |
| GET | `/api/mappings/` | Mappings for your patients |
| GET | `/api/mappings/<patient_id>/` | Doctors assigned to that patient |
| DELETE | `/api/mappings/<id>/` | Remove a mapping |

### Example bodies

```json
// POST /api/auth/register/
{"name": "Alice", "email": "alice@example.com", "password": "StrongPass#123"}

// POST /api/patients/
{"name": "John Doe", "age": 40, "gender": "M", "phone": "9999999999",
 "address": "Delhi", "medical_history": "Hypertension"}

// POST /api/doctors/
{"name": "Meera Rao", "specialization": "Cardiology",
 "email": "meera@hospital.com", "phone": "8888888888", "experience_years": 12}

// POST /api/mappings/
{"patient": 1, "doctor": 1}
```

`gender` is one of `M`, `F`, `O`.

## Design notes

- Users are Django's built-in `User`; the email is stored as the username and the name in `first_name`.
- Patients are private to the user who created them. Mappings are scoped the same way, so one user cannot attach doctors to, or read, another user's patients.
- A doctor can only be assigned to a given patient once (database unique constraint + validation).
- Validation errors return 400 with field messages; unauthenticated requests 401; permission failures 403; missing records 404; database conflicts 409.
