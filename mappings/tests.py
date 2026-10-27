from rest_framework.test import APITestCase


class HealthcareAPITests(APITestCase):
    def register_and_login(self, email="alice@example.com", name="Alice", password="StrongPass#123"):
        r = self.client.post("/api/auth/register/", {"name": name, "email": email, "password": password}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        r = self.client.post("/api/auth/login/", {"email": email, "password": password}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn("access", r.data)
        return r.data["access"]

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def patient_payload(self, **kw):
        base = {"name": "John Doe", "age": 40, "gender": "M", "phone": "9999999999"}
        base.update(kw)
        return base

    def doctor_payload(self, **kw):
        base = {"name": "Meera Rao", "specialization": "Cardiology", "email": "meera@hospital.com", "experience_years": 12}
        base.update(kw)
        return base

    # ---- auth ----
    def test_register_validation_and_duplicates(self):
        r = self.client.post("/api/auth/register/", {"name": "", "email": "bad", "password": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.register_and_login()
        r = self.client.post("/api/auth/register/", {"name": "A2", "email": "ALICE@example.com", "password": "StrongPass#123"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_login_wrong_password(self):
        self.register_and_login()
        r = self.client.post("/api/auth/login/", {"email": "alice@example.com", "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_endpoints_require_auth(self):
        for url in ("/api/patients/", "/api/doctors/", "/api/mappings/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)

    # ---- patients ----
    def test_patient_crud_and_isolation(self):
        t1 = self.register_and_login()
        t2 = self.register_and_login("bob@example.com", "Bob")

        self.auth(t1)
        r = self.client.post("/api/patients/", self.patient_payload(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        pid = r.data["id"]
        self.assertEqual(len(self.client.get("/api/patients/").data), 1)
        self.assertEqual(self.client.get(f"/api/patients/{pid}/").status_code, 200)
        r = self.client.put(f"/api/patients/{pid}/", self.patient_payload(age=41), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["age"], 41)

        # invalid data
        r = self.client.post("/api/patients/", self.patient_payload(age=-3, gender="X"), format="json")
        self.assertEqual(r.status_code, 400)

        # another user can't see/modify/delete it, and sees an empty list
        self.auth(t2)
        self.assertEqual(self.client.get("/api/patients/").data, [])
        self.assertEqual(self.client.get(f"/api/patients/{pid}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/patients/{pid}/").status_code, 404)

        self.auth(t1)
        self.assertEqual(self.client.delete(f"/api/patients/{pid}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/patients/{pid}/").status_code, 404)

    # ---- doctors ----
    def test_doctor_crud_and_permissions(self):
        t1 = self.register_and_login()
        t2 = self.register_and_login("bob@example.com", "Bob")

        self.auth(t1)
        r = self.client.post("/api/doctors/", self.doctor_payload(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        did = r.data["id"]
        # duplicate email
        r = self.client.post("/api/doctors/", self.doctor_payload(), format="json")
        self.assertEqual(r.status_code, 400)

        # any authenticated user can read all doctors, but not modify
        self.auth(t2)
        self.assertEqual(len(self.client.get("/api/doctors/").data), 1)
        self.assertEqual(self.client.get(f"/api/doctors/{did}/").status_code, 200)
        self.assertEqual(self.client.put(f"/api/doctors/{did}/", self.doctor_payload(name="Hacked"), format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/doctors/{did}/").status_code, 403)

        self.auth(t1)
        r = self.client.put(f"/api/doctors/{did}/", self.doctor_payload(experience_years=15), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["experience_years"], 15)
        self.assertEqual(self.client.delete(f"/api/doctors/{did}/").status_code, 204)

    # ---- mappings ----
    def test_mapping_flow(self):
        t1 = self.register_and_login()
        t2 = self.register_and_login("bob@example.com", "Bob")

        self.auth(t1)
        pid = self.client.post("/api/patients/", self.patient_payload(), format="json").data["id"]
        did = self.client.post("/api/doctors/", self.doctor_payload(), format="json").data["id"]
        did2 = self.client.post("/api/doctors/", self.doctor_payload(name="Ravi", email="ravi@hospital.com", specialization="Neurology"), format="json").data["id"]

        r = self.client.post("/api/mappings/", {"patient": pid, "doctor": did}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        mid = r.data["id"]
        self.assertEqual(self.client.post("/api/mappings/", {"patient": pid, "doctor": did}, format="json").status_code, 400)  # duplicate
        self.assertEqual(self.client.post("/api/mappings/", {"patient": pid, "doctor": 9999}, format="json").status_code, 400)  # bad doctor
        self.assertEqual(self.client.post("/api/mappings/", {"patient": pid, "doctor": did2}, format="json").status_code, 201)

        self.assertEqual(len(self.client.get("/api/mappings/").data), 2)
        r = self.client.get(f"/api/mappings/{pid}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["doctors"]), 2)

        # another user cannot map to / read / delete these
        self.auth(t2)
        self.assertEqual(self.client.post("/api/mappings/", {"patient": pid, "doctor": did}, format="json").status_code, 400)
        self.assertEqual(self.client.get(f"/api/mappings/{pid}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/mappings/{mid}/").status_code, 404)
        self.assertEqual(self.client.get("/api/mappings/").data, [])

        self.auth(t1)
        self.assertEqual(self.client.delete(f"/api/mappings/{mid}/").status_code, 204)
        self.assertEqual(len(self.client.get(f"/api/mappings/{pid}/").data["doctors"]), 1)

        # deleting a patient cascades to its mappings
        self.client.delete(f"/api/patients/{pid}/")
        self.assertEqual(self.client.get("/api/mappings/").data, [])
