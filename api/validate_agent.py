"""POST /api/validate_agent -- check student code for safety and correct class names."""
from __future__ import annotations

import traceback
from http.server import BaseHTTPRequestHandler

import sys, os  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import load_student_agents, read_body, send_cors, send_json  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_cors(self)

    def do_POST(self):
        try:
            body = read_body(self)
            student_code = body.get("student_code")
            if not student_code:
                send_json(self, {"valid": False, "error": "No student_code provided"}, 400)
                return

            load_student_agents(student_code)
            send_json(self, {"valid": True})

        except (ValueError, ImportError) as exc:
            send_json(self, {"valid": False, "error": str(exc)}, 400)
        except Exception:
            send_json(self, {"valid": False, "error": traceback.format_exc()}, 500)
