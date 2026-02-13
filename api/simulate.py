"""POST /api/simulate -- run a single simulation episode."""
from __future__ import annotations

import traceback
from http.server import BaseHTTPRequestHandler

# Shared helpers (underscore-prefixed files are not exposed as endpoints)
import sys, os  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import (  # noqa: E402
    build_env_config,
    read_body,
    resolve_agents,
    run_simulation,
    send_cors,
    send_json,
)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_cors(self)

    def do_POST(self):
        try:
            body = read_body(self)
            config = build_env_config(body.get("config", {}))
            proc_cls, rep_cls = resolve_agents(body)
            seed = int(body.get("seed", 42))
            scenario = body.get("scenario", "normal")

            result = run_simulation(config, proc_cls, rep_cls, seed=seed, scenario_name=scenario)
            send_json(self, result)

        except (ValueError, ImportError) as exc:
            send_json(self, {"error": str(exc)}, status=400)
        except Exception:
            send_json(self, {"error": traceback.format_exc()}, status=500)
