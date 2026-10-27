import unittest
import app as classora

class ClassoraTests(unittest.TestCase):
    def setUp(self):
        classora.app.config["TESTING"] = True
        self.client = classora.app.test_client()

    def test_login_page_loads(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CLASSORA", response.data)

    def test_invalid_login_rejected(self):
        response = self.client.post("/login", data={"email": "wrong@example.com", "password": "bad"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"incorrect", response.data)

    def test_student_can_sign_in(self):
        response = self.client.post("/login", data={"email": "student@classora.demo", "password": "Student123!"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Learning materials", response.data)

    def test_student_cannot_upload(self):
        self.client.post("/login", data={"email": "student@classora.demo", "password": "Student123!"})
        response = self.client.get("/upload")
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
