"""POST /api/evaluate -- run N seeds and return summary + representative daily data."""
from __future__ import annotations

import traceback
from http.server import BaseHTTPRequestHandler

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
            scenario = body.get("scenario", "normal")
            n_seeds = int(body.get("n_seeds", 20))
            seed_start = int(body.get("seed_start", 0))

            all_results = []
            for s in range(seed_start, seed_start + n_seeds):
                r = run_simulation(config, proc_cls, rep_cls, seed=s, scenario_name=scenario)
                all_results.append(r)

            # Build per-seed summary rows
            per_seed = []
            for r in all_results:
                k = r["kpis"]
                per_seed.append({
                    "seed": r["meta"]["seed"],
                    "profit": k["total_profit"],
                    "fill_rate": k["fill_rate"],
                    "visits": k["visits_total"],
                    "score": k["score"],
                    "revenue": k["total_revenue"],
                    "procurement": k["total_procurement_cost"],
                    "holding": k["total_holding_cost"],
                    "stockout_pen": k["total_stockout_penalty"],
                })

            n = len(per_seed)
            averages = {
                "profit": round(sum(r["profit"] for r in per_seed) / n, 2),
                "fill_rate": round(sum(r["fill_rate"] for r in per_seed) / n, 4),
                "score": round(sum(r["score"] for r in per_seed) / n, 4),
                "visits": round(sum(r["visits"] for r in per_seed) / n, 1),
            }

            # Representative: median by score
            sorted_results = sorted(all_results, key=lambda r: r["kpis"]["score"])
            median_result = sorted_results[len(sorted_results) // 2]

            send_json(self, {
                "per_seed": per_seed,
                "averages": averages,
                "representative": median_result,
            })

        except (ValueError, ImportError) as exc:
            send_json(self, {"error": str(exc)}, status=400)
        except Exception:
            send_json(self, {"error": traceback.format_exc()}, status=500)
