from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import json
import unittest

import app


class APITestCase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.original_data_file = app.DATA_FILE
        app.DATA_FILE = Path(self.tmp_dir.name) / "messages.json"

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.APIHandler)
        Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.DATA_FILE = self.original_data_file
        self.tmp_dir.cleanup()

    def call(self, method, path, body=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request(method, path, body=body)
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, payload

    def create(self, message):
        return self.call("POST", "/messages", json.dumps({"message": message}))

    def test_health_is_active(self):
        status, payload = self.call("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "active")

    def test_unknown_path_returns_404(self):
        status, _ = self.call("GET", "/tidak-ada")

        self.assertEqual(status, 404)

    def test_create_adds_timestamp(self):
        status, payload = self.create("Halo")

        self.assertEqual(status, 201)
        self.assertEqual(payload["message"]["message"], "Halo")
        self.assertIn("created_at", payload["message"])

    def test_create_rejects_blank_message(self):
        status, _ = self.create("   ")

        self.assertEqual(status, 400)

    def test_create_rejects_long_message(self):
        status, _ = self.create("x" * 501)

        self.assertEqual(status, 400)

    def test_create_rejects_invalid_json(self):
        status, _ = self.call("POST", "/messages", "bukan json")

        self.assertEqual(status, 400)

    def test_create_rejects_non_object_json(self):
        status, _ = self.call("POST", "/messages", "[1, 2]")

        self.assertEqual(status, 400)

    def test_get_by_index(self):
        self.create("Pertama")
        self.create("Kedua")

        status, payload = self.call("GET", "/messages/1")

        self.assertEqual(status, 200)
        self.assertEqual(payload["message"]["message"], "Kedua")

    def test_get_by_unknown_index_returns_404(self):
        status, _ = self.call("GET", "/messages/999")

        self.assertEqual(status, 404)

    def test_get_by_non_integer_index_returns_400(self):
        status, _ = self.call("GET", "/messages/abc")

        self.assertEqual(status, 400)

    def test_delete_removes_message(self):
        self.create("Hapus saya")

        status, _ = self.call("DELETE", "/messages?index=0")
        _, listing = self.call("GET", "/messages")

        self.assertEqual(status, 200)
        self.assertEqual(listing["total"], 0)

    def test_delete_unknown_index_returns_404(self):
        status, _ = self.call("DELETE", "/messages?index=999")

        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
