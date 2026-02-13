"use client";

import { useEffect, useState } from "react";
import type { SimConfig } from "@/lib/types";
import { DEFAULT_CONFIG } from "@/lib/defaults";

const STORAGE_KEY = "vendsim_config";

function load(): SimConfig {
  if (typeof window === "undefined") return { ...DEFAULT_CONFIG };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SimConfig) : { ...DEFAULT_CONFIG };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

function save(cfg: SimConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
}

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <input
        type="number"
        className="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm px-3 py-2 border"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export default function ConfigurePage() {
  const [cfg, setCfg] = useState<SimConfig>(DEFAULT_CONFIG);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setCfg(load());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) save(cfg);
  }, [cfg, hydrated]);

  function set<K extends keyof SimConfig>(key: K, val: SimConfig[K]) {
    setCfg((prev) => ({ ...prev, [key]: val }));
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Simulation Configuration</h1>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Left column */}
        <div className="space-y-6">
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">General</h2>
            <NumberField label="Horizon (days)" value={cfg.horizon_days} onChange={(v) => set("horizon_days", v)} min={10} max={730} step={10} />
            <NumberField label="Initial cash ($)" value={cfg.initial_cash} onChange={(v) => set("initial_cash", v)} min={0} max={100000} step={100} />
          </section>

          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">Procurement constraints</h2>
            <NumberField label="Max PO lines / day" value={cfg.max_po_lines_per_day} onChange={(v) => set("max_po_lines_per_day", v)} min={1} max={50} />
            <NumberField label="Min order qty" value={cfg.min_order_qty} onChange={(v) => set("min_order_qty", v)} min={1} max={100} />
          </section>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">Replenishment constraints</h2>
            <NumberField label="Max visits / 7 days" value={cfg.max_visits_per_7d} onChange={(v) => set("max_visits_per_7d", v)} min={1} max={14} />
            <NumberField label="Max units / visit" value={cfg.max_units_per_visit} onChange={(v) => set("max_units_per_visit", v)} min={1} max={500} />
          </section>

          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">Cost model</h2>
            <NumberField label="Visit fixed cost ($)" value={cfg.visit_fixed_cost} onChange={(v) => set("visit_fixed_cost", v)} min={0} max={500} step={5} />
            <NumberField label="Holding cost ($/unit/day)" value={cfg.holding_cost_per_unit_day} onChange={(v) => set("holding_cost_per_unit_day", v)} min={0} max={1} step={0.005} />
            <NumberField label="Stockout penalty ($/unit)" value={cfg.stockout_penalty_per_unit} onChange={(v) => set("stockout_penalty_per_unit", v)} min={0} max={10} step={0.1} />
          </section>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={() => setCfg({ ...DEFAULT_CONFIG })}
          className="px-4 py-2 text-sm rounded border border-gray-300 hover:bg-gray-100 transition-colors"
        >
          Reset to defaults
        </button>
        <span className="text-sm text-green-600">
          Configuration auto-saved to browser.
        </span>
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
          Current config JSON
        </summary>
        <pre className="mt-2 p-4 bg-gray-100 rounded text-xs overflow-auto">
          {JSON.stringify(cfg, null, 2)}
        </pre>
      </details>
    </div>
  );
}
