import os
import tempfile
import http.client
import json
import threading
import unittest
from pathlib import Path


tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
os.environ["CARESATHI_DB"] = tmp.name

import server


class CareSathiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.init_db()
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.CareSathiHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        Path(tmp.name).unlink(missing_ok=True)

    def request(self, method, path, body=None, cookie=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        connection.request(method, path, json.dumps(body or {}), headers)
        response = connection.getresponse()
        payload = json.loads(response.read())
        set_cookie = response.getheader("Set-Cookie")
        connection.close()
        return response.status, payload, set_cookie

    def test_demo_users_are_seeded(self):
        with server.connect() as db:
            users = db.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        self.assertEqual(users, 3)

    def test_password_hash_roundtrip(self):
        stored = server.password_hash("strong-password")
        self.assertTrue(server.verify_password("strong-password", stored))
        self.assertFalse(server.verify_password("wrong", stored))

    def test_city_matching_handles_minor_typos_and_aliases(self):
        self.assertTrue(server.cities_match("Ahmedbad", "Ahmedabad"))
        self.assertTrue(server.cities_match("Bangalore", "Bengaluru"))
        self.assertFalse(server.cities_match("Pune", "Mumbai"))

    def test_shift_otp_early_end_and_payout_flow(self):
        _, family_login, family_cookie = self.request("POST", "/api/login", {"email": "family@demo.in", "password": "demo123"})
        _, caretaker_login, caretaker_cookie = self.request("POST", "/api/login", {"email": "caretaker@demo.in", "password": "demo123"})
        self.assertEqual(family_login["user"]["role"], "family")
        self.assertEqual(caretaker_login["user"]["role"], "caretaker")

        status, created, _ = self.request("POST", "/api/requests", {
            "patient_name": "Test Patient", "patient_age": 70, "hospital": "Test Hospital",
            "city": "Pune", "ward_room": "A-101", "care_date": "2026-10-01",
            "start_time": "20:00", "hours": 2, "hourly_rate": 120,
        }, family_cookie)
        self.assertEqual(status, 201)
        request_id = created["id"]

        status, accepted, _ = self.request("POST", f"/api/requests/{request_id}/accept", {}, caretaker_cookie)
        self.assertEqual(status, 200)
        self.assertNotIn("start_otp", accepted)

        _, family_requests, _ = self.request("GET", "/api/requests", {}, family_cookie)
        booking = next(item for item in family_requests if item["id"] == request_id)
        otp = booking["start_otp"]
        self.assertEqual(len(otp), 6)

        status, _, _ = self.request("POST", f"/api/requests/{request_id}/start", {"otp": "000000"}, caretaker_cookie)
        self.assertEqual(status, 400)
        status, started, _ = self.request("POST", f"/api/requests/{request_id}/start", {"otp": otp}, caretaker_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(started["status"], "in_progress")

        status, end_requested, _ = self.request("POST", f"/api/requests/{request_id}/request_end", {}, family_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(end_requested["end_requested"], 1)

        status, completed, _ = self.request("POST", f"/api/requests/{request_id}/complete", {}, caretaker_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(completed["status"], "completed")
        self.assertGreaterEqual(completed["actual_minutes"], 1)
        self.assertGreaterEqual(completed["final_amount"], 1)

        status, _, _ = self.request("POST", f"/api/requests/{request_id}/rate", {"stars": 5, "review": "Dependable"}, family_cookie)
        self.assertEqual(status, 200)
        status, _, _ = self.request("POST", f"/api/requests/{request_id}/rate", {"stars": 4, "review": "Clear handover"}, caretaker_cookie)
        self.assertEqual(status, 200)
        status, duplicate, _ = self.request("POST", f"/api/requests/{request_id}/rate", {"stars": 5}, family_cookie)
        self.assertEqual(status, 409)
        self.assertIn("already rated", duplicate["error"])

        status, watch_link, _ = self.request("POST", f"/api/requests/{request_id}/watch_link", {}, family_cookie)
        self.assertEqual(status, 200)
        token = watch_link["token"]
        status, joined, _ = self.request("POST", f"/api/watch/{token}/join", {"name": "Anjali · Daughter"})
        self.assertEqual(status, 200)
        status, watch_room, _ = self.request("GET", f"/api/watch/{token}")
        self.assertEqual(status, 200)
        self.assertEqual(watch_room["viewers"][0]["name"], "Anjali · Daughter")

        status, caretakers, _ = self.request("GET", "/api/caretakers", {}, family_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(caretakers[0]["city"], "Pune")

        # A CareSathi can release an accepted, not-yet-started request back to the marketplace.
        _, releasable, _ = self.request("POST", "/api/requests", {
            "patient_name": "Release Test", "patient_age": 65, "hospital": "Pune Test Hospital",
            "city": "Pune", "ward_room": "B-202", "care_date": "2026-10-02",
            "start_time": "19:00", "hours": 3, "hourly_rate": 150,
        }, family_cookie)
        release_id = releasable["id"]
        self.request("POST", f"/api/requests/{release_id}/accept", {}, caretaker_cookie)
        status, released, _ = self.request("POST", f"/api/requests/{release_id}/release", {"reason": "Personal emergency"}, caretaker_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(released["status"], "open")
        self.assertIsNone(released["caretaker_id"])
        self.assertNotIn("start_otp", released)

        _, family_after_release, _ = self.request("GET", "/api/requests", {}, family_cookie)
        released_for_family = next(item for item in family_after_release if item["id"] == release_id)
        self.assertEqual(released_for_family["last_release_reason"], "Personal emergency")

        _, caretaker_feed, _ = self.request("GET", "/api/requests", {}, caretaker_cookie)
        self.assertIn(release_id, [item["id"] for item in caretaker_feed])

    def test_open_requests_are_seeded(self):
        with server.connect() as db:
            requests = db.execute("SELECT COUNT(*) n FROM care_requests WHERE status='open'").fetchone()["n"]
        self.assertEqual(requests, 0)


if __name__ == "__main__":
    unittest.main()
