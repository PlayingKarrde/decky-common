import json
import os
import sys
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deckycommon import phoneform  # noqa: E402


def req(url, data=None, raw=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    r = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class PhoneFormTests(unittest.TestCase):
    def setUp(self):
        self.got = []

        def submit(fields):
            if not fields.get("sgdb_key"):
                raise ValueError("Paste a SteamGridDB key")
            if fields["sgdb_key"] == "bad":
                raise ValueError("SteamGridDB rejected the API key")
            self.got.append(fields)
            return "Key saved."

        page = lambda: phoneform.shell("Test", "<h1>Test</h1>" + phoneform.sgdb_section(False))  # noqa: E731
        self.f = phoneform.PhoneForm(page, submit).start()
        self.base = f"http://127.0.0.1:{self.f.port}"
        self.addCleanup(self.f.stop)

    def test_flow(self):
        code, page = req(f"{self.base}/{self.f.code.lower()}")  # case-insensitive
        self.assertEqual(code, 200)
        self.assertIn('name="sgdb_key"', page)
        self.assertIn("Send to Deck", page)
        self.assertEqual(req(f"{self.base}/WRONG1")[0], 404)
        _, body = req(f"{self.base}/{self.f.code}", {"sgdb_key": "bad"})
        self.assertEqual(json.loads(body), {"ok": False, "message": "SteamGridDB rejected the API key"})
        self.assertEqual(self.f.state, "waiting")
        _, body = req(f"{self.base}/{self.f.code}", {"sgdb_key": "  abc  ", "n": None, "x": 5})
        self.assertTrue(json.loads(body)["ok"])
        self.assertEqual(self.got, [{"sgdb_key": "abc", "n": "", "x": "5"}])
        self.assertEqual(self.f.status()["state"], "done")
        self.assertEqual(self.f.status()["message"], "Key saved.")
        time.sleep(0.2)
        with self.assertRaises(OSError):  # server is gone
            urllib.request.urlopen(f"{self.base}/{self.f.code}", timeout=2)

    def test_locks_after_guessing(self):
        for _ in range(phoneform.MAX_BAD_REQUESTS):
            req(f"{self.base}/AAAAAA")
        self.assertEqual(self.f.state, "locked")

    def test_rejects_bad_bodies(self):
        self.assertEqual(req(f"{self.base}/{self.f.code}", raw=b"[1]")[0], 400)
        self.assertEqual(req(f"{self.base}/{self.f.code}", raw=b"{")[0], 400)
        self.assertEqual(req(f"{self.base}/{self.f.code}", raw=b"x" * (phoneform.MAX_BODY + 1))[0], 400)
        self.assertEqual(self.f.state, "waiting")

    def test_send_script_reads_only_form_controls(self):
        # Regression: querySelectorAll("[name]") also matched <meta name="viewport">, whose
        # missing .value threw before fetch, so phones showed "Couldn't reach the Deck".
        # (The script itself was checked in Steam's CEF; this pins the selector.)
        page = phoneform.shell("T", phoneform.sgdb_section(False))
        self.assertIn('<meta name="viewport"', page)
        self.assertNotIn('querySelectorAll("[name]")', page)
        self.assertIn("main input[name], main textarea[name]", page)

    def test_sections(self):
        self.assertIn("already saved", phoneform.sgdb_section(True))
        self.assertIn("Optional.", phoneform.sgdb_section(False))
        self.assertNotIn("Optional.", phoneform.sgdb_section(False, optional=False))
        self.assertIn("steamgriddb.com/profile/preferences/api", phoneform.sgdb_section(False))
        self.assertNotIn("<script>", phoneform.shell("<script>", "", form=False).split("<style>")[0])


if __name__ == "__main__":
    unittest.main()
