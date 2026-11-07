import base64
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deckycommon import net, selfupdate  # noqa: E402
from deckycommon.images import CHUNK_BYTES, ImageCache  # noqa: E402
from deckycommon.net import Image, PluginError  # noqa: E402


class SelfUpdateTests(unittest.TestCase):
    def test_versions(self):
        self.assertTrue(selfupdate.is_newer("0.5.0", "0.4.0"))
        self.assertTrue(selfupdate.is_newer("v0.10", "0.9.9"))
        self.assertFalse(selfupdate.is_newer("0.4.0", "0.4"))
        self.assertFalse(selfupdate.is_newer("0.5.0-beta", "0.4.0"))  # unparsable: never nag

    def test_check_reads_release(self):
        u = selfupdate.Updater("o/x-decky", "x-decky-")
        release = {"tag_name": "v0.6.0", "html_url": "https://example/rel",
                   "assets": [{"name": "other-0.6.0.zip", "browser_download_url": "https://example/o.zip"},
                              {"name": "x-decky-0.6.0.zip", "browser_download_url": "https://example/z.zip",
                               "digest": "sha256:abc"}]}
        r = u.check("0.5.0", force=True, fetch=lambda: release)
        self.assertEqual((r["newer"], r["latest"], r["url"], r["sha256"]), (True, "0.6.0", "https://example/z.zip", "abc"))
        release["assets"] = []
        self.assertFalse(u.check("0.5.0", force=True, fetch=lambda: release)["newer"])
        self.assertEqual(u.latest_url, "https://api.github.com/repos/o/x-decky/releases/latest")


class NetTests(unittest.TestCase):
    def test_user_agent(self):
        old = net.user_agent()
        try:
            net.set_user_agent("x-decky/1.0")
            self.assertEqual(net.user_agent(), "x-decky/1.0")
        finally:
            net.set_user_agent(old)

    def test_error_envelope(self):
        self.assertEqual(PluginError("nope", status=404, code="x").to_dict(),
                         {"message": "nope", "status": 404, "code": "x"})


PNG = b"\x89PNG\r\n\x1a\n" + b"x" * (CHUNK_BYTES + 10)


class ImageCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def fetch(self, url):
        self.calls.append(url)
        return Image(PNG, "image/png")

    def test_describe_chunks_and_thumbnail(self):
        c = ImageCache(self.tmp.name)
        d = c.describe(self.fetch, "/a/cover.png")
        self.assertEqual((d["content_type"], d["chunks"]), ("image/png", 2))
        self.assertEqual(base64.b64decode(c.chunk("/a/cover.png", 0) + c.chunk("/a/cover.png", 1)), PNG)
        jpeg = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff" + b"j" * 10).decode()
        c.save_thumbnail("/a/cover.png", jpeg)
        self.assertEqual(c.describe(self.fetch, "/a/cover.png"), {"thumb": jpeg})
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(PluginError):
            c.save_thumbnail("/a/cover.png", "data:image/png;base64,AAAA")

    def test_ignore_query(self):
        c = ImageCache(self.tmp.name, ignore_query=True)
        c.describe(self.fetch, "/a.png?ts=1")
        c.describe(self.fetch, "/a.png?ts=2")
        self.assertEqual(len(self.calls), 1)
        c2 = ImageCache(self.tmp.name)
        c2.describe(self.fetch, "/b.png?ts=1")
        c2.describe(self.fetch, "/b.png?ts=2")
        self.assertEqual(len(self.calls), 3)

    def test_drop_original_and_bad_type(self):
        c = ImageCache(self.tmp.name)
        c.describe_original(self.fetch, "/h.png")
        c.drop_original("/h.png")
        c.drop_original("/h.png")
        with self.assertRaises(PluginError):
            c.chunk("/h.png", 0)
        with self.assertRaises(PluginError):
            c.describe(lambda u: Image(b"x", "text/html"), "/bad")


if __name__ == "__main__":
    unittest.main()
