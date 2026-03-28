import base64
import http.server
import json
import logging
import shutil
import threading
import webbrowser
from pathlib import Path

from finder.models import FilteredImage

logger = logging.getLogger(__name__)


def _image_to_data_uri(path: Path, max_thumb: int = 300) -> str:
    """Convert image to a base64 data URI for embedding in HTML."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    # Create thumbnail for fast loading
    img.thumbnail((max_thumb, max_thumb))
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _build_gallery_html(name: str, images: list[FilteredImage]) -> str:
    """Build an HTML gallery page for reviewing images."""
    cards = []
    for i, img in enumerate(images):
        data_uri = _image_to_data_uri(img.path)
        cards.append(f"""
        <div class="card selected" data-index="{i}" onclick="toggle(this)">
            <img src="{data_uri}" />
            <div class="badge">{i+1}</div>
            <div class="reject-x">&times;</div>
        </div>""")

    return f"""<!DOCTYPE html>
<html>
<head>
<title>Review: {name}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #1a1a2e; color: #eee; font-family: -apple-system, sans-serif; padding: 20px; }}
    h1 {{ text-align: center; margin-bottom: 5px; font-size: 24px; }}
    .subtitle {{ text-align: center; color: #888; margin-bottom: 20px; font-size: 14px; }}
    .grid {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }}
    .card {{
        position: relative; width: 200px; height: 200px; border-radius: 8px;
        overflow: hidden; cursor: pointer; border: 3px solid #4CAF50;
        transition: all 0.15s ease;
    }}
    .card img {{ width: 100%; height: 100%; object-fit: cover; }}
    .card.rejected {{ border-color: #f44336; opacity: 0.35; }}
    .card.rejected .reject-x {{ display: block; }}
    .card .reject-x {{
        display: none; position: absolute; top: 50%; left: 50%;
        transform: translate(-50%, -50%); font-size: 80px; color: #f44336;
        font-weight: bold; text-shadow: 0 0 10px rgba(0,0,0,0.8);
    }}
    .badge {{
        position: absolute; top: 5px; left: 5px; background: rgba(0,0,0,0.7);
        color: #fff; padding: 2px 7px; border-radius: 4px; font-size: 12px;
    }}
    .actions {{
        text-align: center; margin: 25px 0; display: flex; gap: 12px;
        justify-content: center; flex-wrap: wrap;
    }}
    button {{
        padding: 12px 28px; border: none; border-radius: 6px; font-size: 16px;
        cursor: pointer; font-weight: 600;
    }}
    .save {{ background: #4CAF50; color: white; }}
    .save:hover {{ background: #45a049; }}
    .reject-all {{ background: #666; color: white; }}
    .reject-all:hover {{ background: #555; }}
    .select-all {{ background: #2196F3; color: white; }}
    .select-all:hover {{ background: #1976D2; }}
    .counter {{ text-align: center; font-size: 18px; margin: 15px 0; color: #4CAF50; }}
</style>
</head>
<body>
    <h1>Review images for: {name}</h1>
    <p class="subtitle">Click images to reject them. Green border = keep, faded with X = reject.</p>
    <div class="counter" id="counter"></div>
    <div class="actions">
        <button class="select-all" onclick="selectAll()">Select All</button>
        <button class="reject-all" onclick="rejectAll()">Reject All</button>
        <button class="save" onclick="save()">Save Selected</button>
    </div>
    <div class="grid">
        {"".join(cards)}
    </div>
    <div class="actions">
        <button class="save" onclick="save()">Save Selected</button>
    </div>
    <script>
        function updateCounter() {{
            const total = document.querySelectorAll('.card').length;
            const selected = document.querySelectorAll('.card.selected').length;
            document.getElementById('counter').textContent = selected + ' / ' + total + ' selected';
        }}
        function toggle(el) {{
            el.classList.toggle('selected');
            el.classList.toggle('rejected');
            updateCounter();
        }}
        function selectAll() {{
            document.querySelectorAll('.card').forEach(c => {{
                c.classList.add('selected');
                c.classList.remove('rejected');
            }});
            updateCounter();
        }}
        function rejectAll() {{
            document.querySelectorAll('.card').forEach(c => {{
                c.classList.remove('selected');
                c.classList.add('rejected');
            }});
            updateCounter();
        }}
        function save() {{
            const selected = [];
            document.querySelectorAll('.card.selected').forEach(c => {{
                selected.push(parseInt(c.dataset.index));
            }});
            fetch('/save', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{selected: selected}})
            }}).then(r => r.json()).then(data => {{
                document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:80vh;flex-direction:column">' +
                    '<h1 style="color:#4CAF50">Saved ' + data.count + ' images</h1>' +
                    '<p style="color:#888;margin-top:10px">You can close this tab.</p></div>';
            }});
        }}
        updateCounter();
    </script>
</body>
</html>"""


def review_and_select(
    name: str,
    images: list[FilteredImage],
    output_dir: Path,
) -> int:
    """Open a browser gallery for the user to review images. Returns count of saved images."""
    if not images:
        return 0

    html = _build_gallery_html(name, images)
    selected_indices: list[int] | None = None
    event = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        def do_POST(self):
            nonlocal selected_indices
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            selected_indices = body.get("selected", [])

            # Save selected images
            output_dir.mkdir(parents=True, exist_ok=True)
            count = 0
            for idx in sorted(selected_indices):
                if 0 <= idx < len(images):
                    img = images[idx]
                    ext = img.path.suffix or ".jpg"
                    dest = output_dir / f"{count + 1:03d}{ext}"
                    shutil.copy2(img.path, dest)
                    count += 1

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"count": count}).encode())
            event.set()

        def log_message(self, format, *args):
            pass  # Suppress server logs

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    print(f"  Opening review gallery for {name} ({len(images)} images)...")
    webbrowser.open(url)

    # Wait for user to click Save
    event.wait()
    server.shutdown()

    count = len(selected_indices) if selected_indices else 0
    return count
