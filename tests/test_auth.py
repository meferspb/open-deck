"""Тесты парольной аутентификации: хеш, сессии, лимит попыток."""

import tempfile
import unittest
from pathlib import Path

from msfs_gateway import auth
from msfs_gateway.auth import AuthService, LoginLimiter, SessionStore


class PasswordTest(unittest.TestCase):
    def test_short_password_rejected(self):
        self.assertIn("6", auth.validate_password("abc"))
        self.assertIsNone(auth.validate_password("abcdef"))

    def test_hash_and_verify(self):
        record = auth.hash_password("correct horse")
        self.assertTrue(auth.verify_password("correct horse", record))
        self.assertFalse(auth.verify_password("correct hors", record))
        self.assertFalse(auth.verify_password("", record))

    def test_corrupted_record_is_not_valid(self):
        self.assertFalse(auth.verify_password("x", {}))
        self.assertFalse(auth.verify_password("x", {"algorithm": "md5"}))
        self.assertFalse(auth.verify_password("x", {"hash": "not-base64", "salt": "x"}))

    def test_file_roundtrip_and_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            self.assertIsNone(auth.load_record(path))
            auth.save_record(path, "secret123")
            record = auth.load_record(path)
            self.assertTrue(auth.verify_password("secret123", record))
            self.assertFalse(auth.verify_password("secret124", record))

    def test_malformed_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(auth.AuthError):
                auth.load_record(path)


class SessionTest(unittest.TestCase):
    def test_create_and_validate(self):
        store = SessionStore(ttl=10.0)
        token = store.create()
        self.assertTrue(store.validate(token))
        self.assertFalse(store.validate("nope"))
        self.assertFalse(store.validate(None))

    def test_expiry(self):
        store = SessionStore(ttl=0.01)
        token = store.create()
        self.assertTrue(store.validate(token, touch=False))
        import time

        time.sleep(0.03)
        self.assertFalse(store.validate(token, touch=False))

    def test_touch_extends(self):
        store = SessionStore(ttl=0.05)
        token = store.create()
        import time

        time.sleep(0.03)
        self.assertTrue(store.validate(token))  # продлили
        time.sleep(0.03)
        self.assertTrue(store.validate(token, touch=False))

    def test_revoke(self):
        store = SessionStore()
        token = store.create()
        store.revoke(token)
        self.assertFalse(store.validate(token))

    def test_pairing_is_single_use(self):
        store = SessionStore()
        token = store.create(ttl=10.0, pairing=True)
        session = store.consume_pairing(token)
        self.assertIsNotNone(session)
        self.assertTrue(store.validate(session))
        self.assertIsNone(store.consume_pairing(token))
        self.assertFalse(store.validate(token))


class LimiterTest(unittest.TestCase):
    def test_blocks_after_failures(self):
        limiter = LoginLimiter(max_failures=3, window=60.0, lockout=30.0)
        limiter.register_failure("1.2.3.4")
        limiter.register_failure("1.2.3.4")
        self.assertEqual(limiter.retry_after("1.2.3.4"), 0.0)
        limiter.register_failure("1.2.3.4")
        self.assertGreater(limiter.retry_after("1.2.3.4"), 0.0)
        # Другой адрес не страдает.
        self.assertEqual(limiter.retry_after("5.6.7.8"), 0.0)
        limiter.reset("1.2.3.4")
        self.assertEqual(limiter.retry_after("1.2.3.4"), 0.0)


class ServiceTest(unittest.TestCase):
    def test_open_mode_allows_everything(self):
        service = AuthService()
        self.assertFalse(service.required)
        self.assertTrue(service.valid(None))
        self.assertEqual(service.login("anything"), None)  # ничего не проверяем

    def test_login_flow(self):
        service = AuthService(record=auth.hash_password("secret123"))
        self.assertTrue(service.required)
        self.assertFalse(service.valid(None))
        self.assertIsNone(service.login("wrong"))
        token = service.login("secret123")
        self.assertIsNotNone(token)
        self.assertTrue(service.valid(token))
        service.sessions.revoke(token)
        self.assertFalse(service.valid(token))

    def test_pairing_session_created(self):
        service = AuthService(record=auth.hash_password("secret123"))
        token = service.issue_pairing()
        session = service.sessions.consume_pairing(token)
        self.assertIsNotNone(session)
        self.assertTrue(service.valid(session))


if __name__ == "__main__":
    unittest.main()
