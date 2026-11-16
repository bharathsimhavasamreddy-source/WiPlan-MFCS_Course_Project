"""
wiplan.server
Lightweight, zero-dependency HTTP API & Static File Server.
Built on Python standard library http.server.
Serves REST API endpoints for all algorithmic steps and the interactive web GUI.
"""

import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from .graph import CampusGraph, AccessPoint, Student
from .presets import PRESET_MAP, load_preset
from .bipartite import check_bipartite
from .sat_solver import solve_3_channel_sat
from .spectral import (
    Why1611Proof,
    generate_aci_matrix,
    solve_11_channel_spectral,
)
from .local_search import (
    local_search_min_conflicts,
    simulate_random_vs_local_search,
)
from .matching import solve_student_ap_matching
from .kempe import kempe_recolor_for_new_ap
from .algorithms import run_all_benchmarks


STATIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "static")
)

# In-memory session state (defaults to main campus)
CURRENT_GRAPH: CampusGraph = load_preset("campus_main")


class WiPlanRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format: str, *args: Any):
        # Concise logging
        # print(f"[{self.log_date_time_string()}] {format % args}")
        pass

    def send_json(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def get_parsed_body(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def get_effective_graph(self, body: Dict[str, Any]) -> CampusGraph:
        global CURRENT_GRAPH
        if "graph" in body and body["graph"]:
            return CampusGraph.from_dict(body["graph"])
        return CURRENT_GRAPH

    def do_GET(self):
        global CURRENT_GRAPH
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/status":
            self.send_json(200, {
                "status": "ok",
                "version": "1.0.0",
                "graph_name": CURRENT_GRAPH.name,
                "ap_count": len(CURRENT_GRAPH.aps),
                "edge_count": len(CURRENT_GRAPH.get_interference_edges()),
                "student_count": len(CURRENT_GRAPH.students),
            })
            return

        if path == "/api/presets":
            preset_list = [
                {
                    "key": "small_campus",
                    "title": "Small Campus",
                    "description": "Low-density network · 8 APs",
                },
                {
                    "key": "hostel_cluster",
                    "title": "Hostel Cluster",
                    "description": "Multiple nearby APs · 10 APs",
                },
                {
                    "key": "library_labs",
                    "title": "Library & Labs",
                    "description": "Dense indoor coverage · 12 APs",
                },
                {
                    "key": "dense_campus",
                    "title": "Dense Campus",
                    "description": "High AP density · 10 APs",
                },
                {
                    "key": "high_interference",
                    "title": "High Interference",
                    "description": "Heavy channel contention · 11 APs",
                },
                {
                    "key": "full_campus",
                    "title": "Full Campus",
                    "description": "Larger multi-zone network · 15 APs",
                },
            ]
            self.send_json(200, {"presets": preset_list})
            return

        if path.startswith("/api/preset/"):
            preset_key = path.split("/api/preset/")[1]
            if preset_key in PRESET_MAP:
                CURRENT_GRAPH = load_preset(preset_key)
                self.send_json(200, {
                    "success": True,
                    "preset": preset_key,
                    "graph": CURRENT_GRAPH.to_dict(),
                })
            else:
                self.send_json(404, {"error": f"Unknown preset: {preset_key}"})
            return

        if path == "/api/graph":
            self.send_json(200, CURRENT_GRAPH.to_dict())
            return

        if path == "/api/step3-spectral-proof":
            proof = Why1611Proof.get_formal_proof()
            aci_matrix = generate_aci_matrix()
            self.send_json(200, {
                "proof": proof,
                "aci_matrix": aci_matrix,
            })
            return

        # Serve static frontend files
        self.serve_static_file(path)

    def do_POST(self):
        global CURRENT_GRAPH
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self.get_parsed_body()

        if path == "/api/update-graph":
            if "graph" in body:
                CURRENT_GRAPH = CampusGraph.from_dict(body["graph"])
                self.send_json(200, {"success": True, "graph": CURRENT_GRAPH.to_dict()})
            else:
                self.send_json(400, {"error": "Missing graph data in body"})
            return

        if path == "/api/step1-bipartite":
            g = self.get_effective_graph(body)
            result = check_bipartite(g)
            self.send_json(200, result.to_dict())
            return

        if path == "/api/step2-sat":
            g = self.get_effective_graph(body)
            channels = body.get("channels", [1, 6, 11])
            result = solve_3_channel_sat(g, channels=channels)
            self.send_json(200, result.to_dict())
            return

        if path == "/api/step3-spectral-solve":
            g = self.get_effective_graph(body)
            min_sep = int(body.get("min_separation", 5))
            result = solve_11_channel_spectral(g, min_separation=min_sep)
            self.send_json(200, result)
            return

        if path == "/api/step4-local-search":
            g = self.get_effective_graph(body)
            channels = body.get("channels", [1, 6, 11])
            max_steps = int(body.get("max_steps", 500))
            seed = body.get("seed", 42)
            result = local_search_min_conflicts(g, channels=channels, max_steps=max_steps, seed=seed)
            self.send_json(200, result.to_dict())
            return

        if path == "/api/step4-simulation":
            g = self.get_effective_graph(body)
            trials = int(body.get("trials", 100))
            channels = body.get("channels", [1, 6, 11])
            result = simulate_random_vs_local_search(g, trials=trials, channels=channels)
            self.send_json(200, result)
            return

        if path == "/api/step5-matching":
            g = self.get_effective_graph(body)
            result = solve_student_ap_matching(g)
            self.send_json(200, result.to_dict())
            return

        if path == "/api/bonus-kempe":
            g = self.get_effective_graph(body)
            current_coloring = body.get("coloring", {})
            # If new AP data is provided in body, use it; else create a test AP
            if "new_ap" in body:
                new_ap = AccessPoint.from_dict(body["new_ap"])
            else:
                # Default test AP
                new_ap = AccessPoint("AP-NEW", "Expansion AP", 310, 160, capacity=5)

            result = kempe_recolor_for_new_ap(g, new_ap, current_coloring)
            result["new_ap"] = new_ap.to_dict()
            self.send_json(200, result)
            return

        if path == "/api/benchmark":
            g = self.get_effective_graph(body)
            result = run_all_benchmarks(g)
            self.send_json(200, result)
            return

        self.send_json(404, {"error": f"Unknown endpoint: {path}"})

    def serve_static_file(self, req_path: str):
        if req_path in ("/", ""):
            req_path = "/index.html"

        # Sanitize path to prevent directory traversal
        rel_path = req_path.lstrip("/")
        full_path = os.path.abspath(os.path.join(STATIC_DIR, rel_path))

        if not full_path.startswith(STATIC_DIR) or not os.path.isfile(full_path):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        ext = os.path.splitext(full_path)[1].lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        ctype = content_types.get(ext, "application/octet-stream")

        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Server error: {e}".encode("utf-8"))


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def run_server(port: int = 8000, host: str = "0.0.0.0"):
    server_address = (host, port)
    try:
        httpd = ReusableHTTPServer(server_address, WiPlanRequestHandler)
    except OSError as e:
        if getattr(e, "errno", None) == 48 or "Address already in use" in str(e):
            print(f"\n❌ Error: Port {port} is already in use by another process.")
            print(f"👉 Free port {port}:  lsof -ti:{port} | xargs kill -9")
            print(f"👉 Or start on a different port:  python3 run.py --port 8080\n")
            return
        raise e
    print(f"🚀 WiPlan Server running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping WiPlan server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
