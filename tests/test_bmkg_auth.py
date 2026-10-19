"""Authentication regression tests; no network requests or real secrets."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src import download_aws as aws


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


class TestBmkgLogin(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"AWS_API_TOKEN": "", "AWS_API_USERNAME": "tester", "AWS_API_PASSWORD": "SECRET_VALUE"}, clear=False)
        self.env.start()
        self.sleep = patch("src.download_aws.time.sleep")
        self.sleep.start()
    def tearDown(self):
        self.sleep.stop()
        self.env.stop()

    def test_retry_500_then_success(self):
        s = FakeSession([FakeResponse(500), FakeResponse(200, {"status": "sukses", "token": "issued-token"})])
        self.assertEqual(aws.get_token(s), "issued-token")
        self.assertEqual(len(s.calls), 2)
        self.assertEqual(s.calls[0][1]["params"]["username"], "tester")
        self.assertEqual(s.calls[0][1]["params"]["password"], "SECRET_VALUE")

    def test_repeated_500_omits_credentials(self):
        s = FakeSession([FakeResponse(500)] * 3)
        with self.assertRaises(RuntimeError) as ctx:
            aws.get_token(s)
        self.assertIn("HTTP 500", str(ctx.exception))
        self.assertEqual(len(s.calls), 3)
        self.assertNotIn("SECRET_VALUE", str(ctx.exception))
        self.assertNotIn("username=", str(ctx.exception))

    def test_401_not_retried_and_no_url(self):
        s = FakeSession([FakeResponse(401)])
        with self.assertRaises(RuntimeError) as ctx:
            aws.get_token(s)
        self.assertEqual(len(s.calls), 1)
        self.assertNotIn("SECRET_VALUE", str(ctx.exception))
        self.assertNotIn("username=", str(ctx.exception))

    def test_env_token_bypasses_auth(self):
        os.environ["AWS_API_TOKEN"] = "cached-token"
        s = FakeSession([])
        self.assertEqual(aws.get_token(s), "cached-token")
        self.assertEqual(s.calls, [])


if __name__ == "__main__":
    unittest.main()
