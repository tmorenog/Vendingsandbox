"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DEFAULT_CONFIG } from "@/lib/defaults";
import type {
  AgentMode,
  DailyEntry,
  EvaluateResult,
  Kpis,
  RunMode,
  Scenario,
  SimConfig,
  SimulationResult,
} from "@/lib/types";
import { SCENARIOS } from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "vendsim_config";

function loadConfig(): SimConfig {
  if (typeof window === "undefined") return { ...DEFAULT_CONFIG };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SimConfig) : { ...DEFAULT_CONFIG };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

function cumulative(values: number[]): number[] {
  const out: number[] = [];
  let total = 0;
  for (const v of values) {
    total += v;
    out.push(Math.round(total * 100) / 100);
  }
  return out;
}

const SKU_COLORS = [
  "#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#9333ea", "#0891b2",
  "#e11d48", "#65a30d", "#c026d3", "#0d9488", "#ea580c", "#4f46e5",
];

async function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result as string);
    r.onerror = reject;
    r.readAsText(file);
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KpiCards({ kpis }: { kpis: Kpis }) {
  const items: { label: string; value: string }[] = [
    { label: "Total Profit", value: `$${kpis.total_profit.toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
    { label: "Fill Rate", value: `${(kpis.fill_rate * 100).toFixed(1)}%` },
    { label: "Score", value: kpis.score.toFixed(4) },
    { label: "Visits", value: String(kpis.visits_total) },
    { label: "Revenue", value: `$${kpis.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
    { label: "Procurement", value: `$${kpis.total_procurement_cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
    { label: "Holding Cost", value: `$${kpis.total_holding_cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
    { label: "Stockout Penalty", value: `$${kpis.total_stockout_penalty.toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {items.map((it) => (
        <div key={it.label} className="bg-white rounded-lg border p-4">
          <p className="text-xs text-gray-500">{it.label}</p>
          <p className="text-lg font-semibold mt-1">{it.value}</p>
        </div>
      ))}
    </div>
  );
}

function DailyCharts({ daily }: { daily: DailyEntry[] }) {
  const [selectedSkus, setSelectedSkus] = useState<string[]>([]);
  const allSkus = useMemo(
    () => Object.keys(daily[0]?.machine_on_hand ?? {}).sort(),
    [daily],
  );

  useEffect(() => {
    setSelectedSkus(allSkus.slice(0, 3));
  }, [allSkus]);

  const cumProfits = cumulative(daily.map((d) => d.profit));

  const chartData = daily.map((d, i) => ({
    day: d.day,
    profit: d.profit,
    cumProfit: cumProfits[i],
    cash: d.cash,
    fillRate: d.fill_rate,
    sold: d.units_sold,
    lost: -d.units_lost,
  }));

  return (
    <div className="space-y-8">
      {/* Profit */}
      <div className="grid md:grid-cols-2 gap-6">
        <ChartCard title="Daily Profit">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <ReferenceLine y={0} stroke="#888" />
              <Bar dataKey="profit" fill="#4682b4" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Cumulative Profit">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <ReferenceLine y={0} stroke="#888" />
              <Area dataKey="cumProfit" stroke="#166534" fill="#bbf7d0" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Cash & Fill Rate */}
      <div className="grid md:grid-cols-2 gap-6">
        <ChartCard title="Cash on Hand">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area dataKey="cash" stroke="#ea580c" fill="#fed7aa" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Daily Fill Rate">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 1.05]} tick={{ fontSize: 11 }} />
              <Tooltip />
              <ReferenceLine
                y={0.7}
                stroke="#ef4444"
                strokeDasharray="6 3"
                label={{ value: "Churn 70%", fill: "#ef4444", fontSize: 10 }}
              />
              <Line dataKey="fillRate" stroke="#0d9488" dot={false} strokeWidth={1.5} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Sold vs Lost */}
      <ChartCard title="Units Sold vs Lost Sales">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <ReferenceLine y={0} stroke="#888" />
            <Bar dataKey="sold" fill="#3cb371" name="Sold" />
            <Bar dataKey="lost" fill="#cd5c5c" name="Lost (neg)" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Inventory trajectories */}
      <ChartCard title="Inventory Trajectories">
        <div className="mb-3 flex flex-wrap gap-2">
          {allSkus.map((sku) => (
            <button
              key={sku}
              onClick={() =>
                setSelectedSkus((prev) =>
                  prev.includes(sku)
                    ? prev.filter((s) => s !== sku)
                    : [...prev, sku],
                )
              }
              className={`text-xs px-2 py-1 rounded border transition-colors ${
                selectedSkus.includes(sku)
                  ? "bg-blue-100 border-blue-400 text-blue-800"
                  : "bg-gray-50 border-gray-200 text-gray-500"
              }`}
            >
              {sku}
            </button>
          ))}
        </div>
        {selectedSkus.length > 0 && (
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Machine</p>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart
                  data={daily.map((d) => ({ day: d.day, ...d.machine_on_hand }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
                  {selectedSkus.map((sku, i) => (
                    <Line
                      key={sku}
                      dataKey={sku}
                      stroke={SKU_COLORS[i % SKU_COLORS.length]}
                      dot={false}
                      strokeWidth={1.2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Stockroom</p>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart
                  data={daily.map((d) => ({ day: d.day, ...d.stockroom_on_hand }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
                  {selectedSkus.map((sku, i) => (
                    <Line
                      key={sku}
                      dataKey={sku}
                      stroke={SKU_COLORS[i % SKU_COLORS.length]}
                      dot={false}
                      strokeWidth={1.2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </ChartCard>
    </div>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function RunPage() {
  // --- state ---
  const [agentMode, setAgentMode] = useState<AgentMode>("baseline");
  const [procCode, setProcCode] = useState("");
  const [repCode, setRepCode] = useState("");
  const procFileRef = useRef<HTMLInputElement>(null);
  const repFileRef = useRef<HTMLInputElement>(null);

  const [scenario, setScenario] = useState<Scenario>("normal");
  const [runMode, setRunMode] = useState<RunMode>("single");
  const [seed, setSeed] = useState(42);
  const [nSeeds, setNSeeds] = useState(20);
  const [seedStart, setSeedStart] = useState(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [singleResult, setSingleResult] = useState<SimulationResult | null>(null);
  const [evalResult, setEvalResult] = useState<EvaluateResult | null>(null);

  // --- helpers ---
  function studentCode() {
    return { procurement: procCode, replenishment: repCode };
  }

  function canRun(): boolean {
    if (agentMode === "baseline") return true;
    return procCode.trim().length > 0 && repCode.trim().length > 0;
  }

  async function handleFileSelect(
    e: React.ChangeEvent<HTMLInputElement>,
    setter: (v: string) => void,
  ) {
    const file = e.target.files?.[0];
    if (file) setter(await readFileText(file));
  }

  async function handleRun() {
    setLoading(true);
    setError("");
    setSingleResult(null);
    setEvalResult(null);
    const config = loadConfig();

    try {
      if (runMode === "single") {
        const res = await fetch("/api/simulate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            config,
            agent_type: agentMode === "baseline" ? "baseline" : "student",
            scenario,
            seed,
            ...(agentMode !== "baseline" && { student_code: studentCode() }),
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Simulation failed");
        setSingleResult(data as SimulationResult);
      } else {
        const res = await fetch("/api/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            config,
            agent_type: agentMode === "baseline" ? "baseline" : "student",
            scenario,
            n_seeds: nSeeds,
            seed_start: seedStart,
            ...(agentMode !== "baseline" && { student_code: studentCode() }),
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Evaluation failed");
        setEvalResult(data as EvaluateResult);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  // --- render ---
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Run Simulation</h1>

      {/* ── Agent Selection ── */}
      <section className="space-y-4">
        <h2 className="font-semibold">Agent Selection</h2>
        <div className="flex gap-2">
          {(["baseline", "upload", "paste"] as AgentMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setAgentMode(m)}
              className={`px-4 py-2 text-sm rounded border transition-colors ${
                agentMode === m
                  ? "bg-blue-50 border-blue-400 text-blue-700"
                  : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {m === "baseline" ? "Baseline" : m === "upload" ? "Upload .py" : "Paste code"}
            </button>
          ))}
        </div>

        {agentMode === "upload" && (
          <div className="grid sm:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-gray-600">student_procurement.py</span>
              <input
                ref={procFileRef}
                type="file"
                accept=".py"
                onChange={(e) => handleFileSelect(e, setProcCode)}
                className="mt-1 block w-full text-sm file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
              />
            </label>
            <label className="block">
              <span className="text-sm text-gray-600">student_replenishment.py</span>
              <input
                ref={repFileRef}
                type="file"
                accept=".py"
                onChange={(e) => handleFileSelect(e, setRepCode)}
                className="mt-1 block w-full text-sm file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
              />
            </label>
          </div>
        )}

        {agentMode === "paste" && (
          <div className="grid sm:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-gray-600">student_procurement.py</span>
              <textarea
                rows={12}
                className="mt-1 block w-full rounded border border-gray-300 text-xs font-mono p-3 focus:border-blue-500 focus:ring-blue-500"
                placeholder={"class StudentProcurementAgent:\n    def act(self, obs):\n        return {'pos': [], 'note': ''}"}
                value={procCode}
                onChange={(e) => setProcCode(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-sm text-gray-600">student_replenishment.py</span>
              <textarea
                rows={12}
                className="mt-1 block w-full rounded border border-gray-300 text-xs font-mono p-3 focus:border-blue-500 focus:ring-blue-500"
                placeholder={"class StudentReplenishmentAgent:\n    def act(self, obs):\n        return {'visit': False, 'restock': {}, 'note': ''}"}
                value={repCode}
                onChange={(e) => setRepCode(e.target.value)}
              />
            </label>
          </div>
        )}
      </section>

      {/* ── Scenario ── */}
      <section className="space-y-2">
        <h2 className="font-semibold">Scenario</h2>
        <select
          value={scenario}
          onChange={(e) => setScenario(e.target.value as Scenario)}
          className="rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500"
        >
          {SCENARIOS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </section>

      {/* ── Run Controls ── */}
      <section className="space-y-4">
        <h2 className="font-semibold">Run Controls</h2>
        <div className="flex gap-4 items-end flex-wrap">
          <div className="flex gap-2">
            {(["single", "evaluate"] as RunMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setRunMode(m)}
                className={`px-3 py-2 text-sm rounded border transition-colors ${
                  runMode === m
                    ? "bg-blue-50 border-blue-400 text-blue-700"
                    : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {m === "single" ? "Single run" : "Evaluate (N seeds)"}
              </button>
            ))}
          </div>

          {runMode === "single" ? (
            <label className="block">
              <span className="text-xs text-gray-500">Seed</span>
              <input
                type="number"
                className="block w-24 rounded border border-gray-300 px-2 py-2 text-sm"
                value={seed}
                min={0}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </label>
          ) : (
            <>
              <label className="block">
                <span className="text-xs text-gray-500"># Seeds</span>
                <input
                  type="number"
                  className="block w-20 rounded border border-gray-300 px-2 py-2 text-sm"
                  value={nSeeds}
                  min={1}
                  max={500}
                  onChange={(e) => setNSeeds(Number(e.target.value))}
                />
              </label>
              <label className="block">
                <span className="text-xs text-gray-500">Start seed</span>
                <input
                  type="number"
                  className="block w-20 rounded border border-gray-300 px-2 py-2 text-sm"
                  value={seedStart}
                  min={0}
                  onChange={(e) => setSeedStart(Number(e.target.value))}
                />
              </label>
            </>
          )}

          <button
            onClick={handleRun}
            disabled={loading || !canRun()}
            className="px-6 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Running..." : "Run"}
          </button>
        </div>
      </section>

      {/* ── Error ── */}
      {error && (
        <details className="bg-red-50 border border-red-200 rounded p-4" open>
          <summary className="text-red-700 font-medium text-sm cursor-pointer">
            Simulation error
          </summary>
          <pre className="mt-2 text-xs text-red-800 whitespace-pre-wrap overflow-auto max-h-64">
            {error}
          </pre>
        </details>
      )}

      {/* ── Single Run Results ── */}
      {singleResult && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold">
            Results &mdash; seed {singleResult.meta.seed}, {singleResult.meta.scenario}
          </h2>
          <KpiCards kpis={singleResult.kpis} />
          <DailyCharts daily={singleResult.daily} />
        </div>
      )}

      {/* ── Evaluate Results ── */}
      {evalResult && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold">
            Evaluation Results &mdash; {evalResult.per_seed.length} seeds, {scenario}
          </h2>

          {/* Average KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border p-4">
              <p className="text-xs text-gray-500">Avg Profit</p>
              <p className="text-lg font-semibold">${evalResult.averages.profit.toLocaleString()}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <p className="text-xs text-gray-500">Avg Fill Rate</p>
              <p className="text-lg font-semibold">{(evalResult.averages.fill_rate * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <p className="text-xs text-gray-500">Avg Score</p>
              <p className="text-lg font-semibold">{evalResult.averages.score.toFixed(4)}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <p className="text-xs text-gray-500">Avg Visits</p>
              <p className="text-lg font-semibold">{evalResult.averages.visits.toFixed(1)}</p>
            </div>
          </div>

          {/* Per-seed table */}
          <div className="bg-white rounded-lg border overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  {["Seed", "Profit", "Fill Rate", "Visits", "Score"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {evalResult.per_seed.map((r) => (
                  <tr key={r.seed} className="border-t">
                    <td className="px-4 py-2">{r.seed}</td>
                    <td className="px-4 py-2">${r.profit.toFixed(2)}</td>
                    <td className="px-4 py-2">{(r.fill_rate * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2">{r.visits}</td>
                    <td className="px-4 py-2 font-medium">{r.score.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Score by seed chart */}
          <ChartCard title="Score by Seed">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={evalResult.per_seed}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="seed" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <ReferenceLine
                  y={evalResult.averages.score}
                  stroke="#ef4444"
                  strokeDasharray="6 3"
                  label={{ value: `Mean ${evalResult.averages.score.toFixed(4)}`, fill: "#ef4444", fontSize: 10 }}
                />
                <Bar dataKey="score" fill="#4682b4" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Representative daily charts */}
          <h3 className="text-lg font-semibold">
            Daily Charts &mdash; representative seed{" "}
            {evalResult.representative.meta.seed} (median score{" "}
            {evalResult.representative.kpis.score.toFixed(4)})
          </h3>
          <KpiCards kpis={evalResult.representative.kpis} />
          <DailyCharts daily={evalResult.representative.daily} />
        </div>
      )}
    </div>
  );
}
