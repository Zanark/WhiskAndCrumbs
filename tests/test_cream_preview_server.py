from functools import partial
from http.server import ThreadingHTTPServer
import importlib.util
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cream_preview_server", ROOT / "experiments/cream-metaballs/serve.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class QuietHandler(preview.Handler):
    def log_message(self, *args):
        pass


class CreamPreviewServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        for name in preview.VERSIONED_FILES:
            (self.directory / name).write_bytes((ROOT / "experiments/cream-metaballs" / name).read_bytes())

    def tearDown(self):
        self.temporary.cleanup()

    def test_each_runtime_or_style_change_gets_a_new_shared_revision(self):
        initial = preview.preview_revision(self.directory)
        self.assertEqual(initial, preview.preview_revision(self.directory))
        for name in preview.VERSIONED_FILES:
            path = self.directory / name
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            self.assertNotEqual(preview.preview_revision(self.directory), initial, name)
            path.write_bytes(original)

    def test_html_versions_both_styles_and_module_without_changing_source(self):
        before = (self.directory / "index.html").read_bytes()
        revision = preview.preview_revision(self.directory)
        page = preview.versioned_index(self.directory, revision).decode()
        for attribute, name in (("href", "preview.css"), ("href", "static-clumps.css"), ("src", "preview.mjs")):
            self.assertIn(f'{attribute}="{name}?v={revision}"', page)
        self.assertIn(f'data-preview-revision="{revision}"', page)
        self.assertEqual((self.directory / "index.html").read_bytes(), before)
        self.assertIn("modelUrl.search = new URL(import.meta.url).search", (self.directory / "preview.mjs").read_text())

    def test_changed_markup_fails_instead_of_silently_serving_unversioned_scripts(self):
        path = self.directory / "index.html"
        path.write_text(path.read_text().replace('src="preview.mjs"', 'src="other.mjs"'))
        with self.assertRaisesRegex(ValueError, "preview.mjs"):
            preview.versioned_index(self.directory, "example")

    def test_html_modules_and_styles_are_fresh_even_with_old_cache_validators(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(self.directory)))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for path in ("/", "/index.html?update=latest", "/preview.mjs?v=current", "/model.mjs?v=current", "/preview.css?v=current", "/static-clumps.css"):
                request = Request(base + path, headers={"If-Modified-Since": "Thu, 31 Dec 2099 23:59:59 GMT", "If-None-Match": '"old"'})
                with urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("no-store", response.headers["Cache-Control"])
                    self.assertTrue(response.read())
                    if path.endswith(".mjs?v=current"):
                        self.assertIn("javascript", response.headers["Content-Type"])
            with urlopen(Request(base + "/", method="HEAD")) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["X-Preview-Revision"], preview.preview_revision(self.directory))
                self.assertEqual(response.read(), b"")
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
