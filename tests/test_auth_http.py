"""Интеграционные тесты входа по паролю на живом HTTP/WebSocket сервере."""

import http.client
import json
import re
import socket
import tempfile
import unittest
from pathlib import Path

from msfs_gateway.app import GatewayApplication
from msfs_gateway.settings import DEFAULT_WEB_DIR, Settings

WS_KEY = "dGhlIHNhbXBsZSBub25jZQ=="
COOKIE_RE = re.compile(r"rud_session=([^;]+)")


class AuthHttpTest(unittest.TestCase):
    password = "secret123"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            host="127.0.0.1",
            port=0,
            web_dir=DEFAULT_WEB_DIR,
            profile_dir=Path(self.tmp.name),
            sim="mock",
            discovery=False,
            wasm=False,
            password=self.password,
        )
        self.app = GatewayApplication(self.settings, check_integrity=False)
        self.app.start_background()
        self.port = self.app.httpd.server_address[1]

    def tearDown(self):
        self.app.shutdown()
        self.tmp.cleanup()

    # --- утилиты -----------------------------------------------------
    def call(self, method, path, *, body=None, headers=None, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = dict(headers or {})
        if cookie:
            hdrs["Cookie"] = f"rud_session={cookie}"
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        try:
            conn.request(method, path, body=payload, headers=hdrs)
            response = conn.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), data
        finally:
            conn.close()

    def login(self, password=None):
        return self.call(
            "POST",
            "/api/auth/login",
            body={"password": self.password if password is None else password},
        )

    def token_from(self, headers):
        match = COOKIE_RE.search(headers.get("Set-Cookie", ""))
        return match.group(1) if match else None

    def ws_status(self, path="/ws", cookie=None, origin=None):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        request = (
            f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {WS_KEY}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
        )
        if cookie:
            request += f"Cookie: rud_session={cookie}\r\n"
        if origin:
            request += f"Origin: {origin}\r\n"
        request += "\r\n"
        try:
            sock.sendall(request.encode("ascii"))
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                head += chunk
            return int(head.split(b" ")[1])
        finally:
            sock.close()

    # --- тесты -------------------------------------------------------
    def test_oversized_body_closes_connection(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        request = (
            f"POST /api/auth/login HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
            "Content-Length: 3000000\r\n\r\n"
        )
        try:
            sock.sendall(request.encode("ascii"))
            sock.settimeout(5)
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            self.assertIn(b" 413 ", response)
        finally:
            sock.close()

    def test_unknown_host_is_rejected(self):
        status, _, body = self.call("GET", "/api/health", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["code"], "host_not_allowed")

    def test_health_and_status_are_public(self):
        status, _, body = self.call("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["authRequired"])

        status, _, body = self.call("GET", "/api/auth/status")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertTrue(payload["required"])
        self.assertFalse(payload["authenticated"])

    def test_protected_api_returns_401(self):
        status, headers, body = self.call("GET", "/api/profiles")
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["code"], "unauthorized")
        self.assertIn("Bearer", headers.get("WWW-Authenticate", ""))

    def test_assist_requires_login(self):
        status, _, body = self.call("GET", "/api/assist")
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["code"], "unauthorized")

    def test_page_redirects_to_login(self):
        status, headers, _ = self.call("GET", "/")
        self.assertEqual(status, 302)
        self.assertTrue(headers["Location"].startswith("/login.html"))

        status, _, _ = self.call("GET", "/login.html")
        self.assertEqual(status, 200)
        status, _, _ = self.call("GET", "/css/login.css")
        self.assertEqual(status, 200)
        status, _, _ = self.call("GET", "/js/login.js")
        self.assertEqual(status, 200)

    def test_login_rejects_wrong_password(self):
        status, headers, body = self.login("wrong-password")
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["code"], "bad_password")
        self.assertNotIn("Set-Cookie", headers)

    def test_login_success_sets_httponly_cookie(self):
        status, headers, body = self.login()
        self.assertEqual(status, 200)
        cookie = headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        token = self.token_from(headers)
        self.assertTrue(token)
        self.assertEqual(json.loads(body)["token"], token)

        status, _, _ = self.call("GET", "/api/profiles", cookie=token)
        self.assertEqual(status, 200)

    def test_bearer_token_works(self):
        _, _headers, body = self.login()
        token = json.loads(body)["token"]
        status, _, _ = self.call(
            "GET", "/api/profiles", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(status, 200)

    def test_websocket_requires_session(self):
        self.assertEqual(self.ws_status(), 401)
        _, _headers, body = self.login()
        token = json.loads(body)["token"]
        self.assertEqual(self.ws_status(cookie=token), 101)
        self.assertEqual(self.ws_status(path=f"/ws?token={token}"), 101)

    def test_websocket_rejects_foreign_origin(self):
        _, _headers, body = self.login()
        token = json.loads(body)["token"]
        self.assertEqual(self.ws_status(cookie=token, origin="http://evil.example"), 403)
        same_origin = f"http://127.0.0.1:{self.port}"
        self.assertEqual(self.ws_status(cookie=token, origin=same_origin), 101)

    def test_pairing_token_is_not_a_session(self):
        _, _headers, body = self.login()
        token = json.loads(body)["token"]
        status, _, body = self.call("POST", "/api/pair", body={}, cookie=token)
        self.assertEqual(status, 200)
        pair_token = json.loads(body)["token"]

        status, _, body = self.call(
            "GET", "/api/profiles", headers={"Authorization": f"Bearer {pair_token}"}
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["code"], "unauthorized")

    def test_post_with_foreign_origin_rejected(self):
        _, _headers, body = self.login()
        token = json.loads(body)["token"]
        status, _, body = self.call(
            "POST",
            "/api/sim/command",
            body={"key": "power.batteryMaster", "value": True},
            cookie=token,
            headers={"Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["code"], "origin_not_allowed")

    def test_logout_revokes_session(self):
        _, headers, _ = self.login()
        token = self.token_from(headers)
        status, _, _ = self.call("POST", "/api/auth/logout", body={}, cookie=token)
        self.assertEqual(status, 200)
        status, _, _ = self.call("GET", "/api/profiles", cookie=token)
        self.assertEqual(status, 401)

    def test_pairing_token_is_single_use(self):
        _, headers, _ = self.login()
        token = self.token_from(headers)

        status, _, body = self.call("POST", "/api/pair", body={}, cookie=token)
        self.assertEqual(status, 200)
        payload = json.loads(body)
        pair_token = payload["token"]
        self.assertIn("?pair=", payload["url"])

        status, headers, _ = self.call("GET", f"/?pair={pair_token}")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "/")
        session = self.token_from(headers)
        self.assertTrue(session)
        status, _, _ = self.call("GET", "/api/profiles", cookie=session)
        self.assertEqual(status, 200)

        # Повторное использование того же QR-кода не даёт сессию.
        status, headers, _ = self.call("GET", f"/?pair={pair_token}")
        self.assertEqual(status, 302)
        self.assertIn("error=pair", headers["Location"])

    def test_rate_limit_blocks_bruteforce(self):
        for _ in range(5):
            status, _, _ = self.login("wrong-password")
            self.assertEqual(status, 401)
        status, headers, body = self.login("wrong-password")
        self.assertEqual(status, 429)
        self.assertIn("Retry-After", headers)
        self.assertGreater(json.loads(body)["retryAfter"], 0)


class OpenModeTest(unittest.TestCase):
    """Без пароля и файла auth.json всё работает как раньше."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            host="127.0.0.1",
            port=0,
            web_dir=DEFAULT_WEB_DIR,
            profile_dir=Path(self.tmp.name),
            sim="mock",
            discovery=False,
            wasm=False,
            auth_path=Path(self.tmp.name) / "auth.json",
        )
        self.app = GatewayApplication(self.settings, check_integrity=False)
        self.app.start_background()
        self.port = self.app.httpd.server_address[1]

    def tearDown(self):
        self.app.shutdown()
        self.tmp.cleanup()

    def call(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path)
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def test_everything_open(self):
        status, body = self.call("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["authRequired"])
        status, _ = self.call("GET", "/api/profiles")
        self.assertEqual(status, 200)
        status, _ = self.call("GET", "/")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
