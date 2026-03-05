"""Local destination — serves files via HTTP + ngrok tunnel."""

from __future__ import annotations

import functools
import html
import http.server
import logging
import os
import threading
import urllib.parse
from typing import Optional

from kgout.destinations.base import BaseDestination

logger = logging.getLogger("kgout")


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


class _FileHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with a cleaner directory listing and silent logs."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        # Suppress default stderr logging
        pass

    def end_headers(self):
        """Inject security headers on every response."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'")
        super().end_headers()

    def translate_path(self, path):
        """Override to block path traversal outside the serve directory."""
        resolved = os.path.realpath(super().translate_path(path))
        serve_root = os.path.realpath(self.directory)
        if not resolved.startswith(serve_root + os.sep) and resolved != serve_root:
            # Attempted traversal — redirect to root
            return serve_root
        return resolved

    def list_directory(self, path):
        """Generate a styled directory listing."""
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "Directory not found")
            return None

        entries.sort(key=lambda e: (not os.path.isdir(os.path.join(path, e)), e.lower()))

        # Build HTML
        display_path = urllib.parse.unquote(self.path)
        lines = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            f"<title>kgout — {html.escape(display_path)}</title>",
            "<style>",
            "  body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a2e; }",
            "  h1 { color: #20beca; font-size: 20px; }",
            "  table { width: 100%; border-collapse: collapse; }",
            "  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eee; }",
            "  th { color: #888; font-size: 12px; text-transform: uppercase; }",
            "  a { color: #2980b9; text-decoration: none; }",
            "  a:hover { text-decoration: underline; }",
            "  .size { color: #888; font-size: 13px; }",
            "  .badge { background: #d4edda; color: #155724; font-size: 11px; padding: 2px 6px; border-radius: 4px; }",
            "</style>",
            "</head><body>",
            f"<h1>📁 kgout <span class='badge'>live</span></h1>",
            f"<p>Serving: <code>{html.escape(display_path)}</code></p>",
            "<table><thead><tr><th>Name</th><th>Size</th></tr></thead><tbody>",
        ]

        if display_path != "/":
            lines.append('<tr><td><a href="..">⬆ ..</a></td><td></td></tr>')

        for entry in entries:
            fullpath = os.path.join(path, entry)
            linkname = entry
            if os.path.isdir(fullpath):
                linkname += "/"
                size_str = "—"
            else:
                try:
                    size_str = _human_size(os.path.getsize(fullpath))
                except OSError:
                    size_str = "?"
            href = urllib.parse.quote(entry, safe="/:@!$&'()*+,;=")
            icon = "📂" if os.path.isdir(fullpath) else "📄"
            lines.append(
                f'<tr><td>{icon} <a href="{href}">{html.escape(linkname)}</a></td>'
                f'<td class="size">{size_str}</td></tr>'
            )

        lines.append("</tbody></table>")
        lines.append("<p style='margin-top: 20px; color: #aaa; font-size: 12px;'>Served by kgout</p>")
        lines.append("</body></html>")

        content = "\n".join(lines).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return None


class LocalDestination(BaseDestination):
    """Expose the watch directory via a local HTTP server + ngrok tunnel.

    Files are browseable and downloadable from the public ngrok URL.
    The watcher callback just logs new files — no upload needed since
    the file server already serves the directory live.
    """

    def __init__(
        self,
        serve_dir: str,
        port: int = 8384,
        ngrok_token: Optional[str] = None,
    ):
        self._serve_dir = serve_dir
        self._port = port
        self._ngrok_token = ngrok_token
        self._httpd: Optional[http.server.HTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None
        self._tunnel = None
        self._public_url: Optional[str] = None

    @property
    def name(self) -> str:
        return "local"

    def start(self):
        # 1. Start HTTP file server
        handler = functools.partial(_FileHandler, directory=self._serve_dir)
        self._httpd = http.server.HTTPServer(("127.0.0.1", self._port), handler)
        self._http_thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="kgout-fileserver",
            daemon=True,
        )
        self._http_thread.start()
        logger.info("🌐 File server started on port %d", self._port)

        # 2. Start ngrok tunnel
        try:
            from pyngrok import ngrok, conf

            if self._ngrok_token:
                conf.get_default().auth_token = self._ngrok_token

            self._tunnel = ngrok.connect(self._port, "http")
            self._public_url = self._tunnel.public_url

            logger.info("=" * 56)
            logger.info("🔗 FILES AVAILABLE AT: %s", self._public_url)
            logger.info("=" * 56)

            # Also print directly so it's visible even if logging is off
            print(f"\n{'='*56}")
            print(f"  📁 kgout — files available at:")
            print(f"  🔗 {self._public_url}")
            print(f"{'='*56}\n")

        except ImportError:
            raise ImportError(
                "pyngrok is required for local destination.\n"
                "Install with: pip install kgout[local]"
            )
        except Exception as exc:
            # Mask ngrok token in error messages to prevent credential leaks
            err_msg = str(exc)
            if self._ngrok_token and self._ngrok_token in err_msg:
                err_msg = err_msg.replace(self._ngrok_token, "***REDACTED***")
            logger.error(
                "Failed to start ngrok tunnel: %s\n"
                "Make sure you have an ngrok auth token set:\n"
                "  - Pass ngrok_token='...' to KgOut, or\n"
                "  - Set NGROK_AUTH_TOKEN environment variable, or\n"
                "  - Run: ngrok config add-authtoken YOUR_TOKEN",
                err_msg,
            )
            # File server still works on localhost even without tunnel
            logger.info(
                "📡 File server still running locally at http://localhost:%d",
                self._port,
            )

    def stop(self):
        if self._tunnel:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(self._tunnel.public_url)
            except Exception:
                pass
            self._tunnel = None

        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None

        self._http_thread = None
        self._public_url = None

    def sync(self, filepath: str, relpath: str, event: str):
        """No upload needed — the file server serves the directory live.
        Just log the availability."""
        if self._public_url:
            url = f"{self._public_url}/{urllib.parse.quote(relpath)}"
            logger.info("   ↳ Download: %s", url)
