import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Vending Machine Digital Ops Sandbox</h1>

      <p className="text-gray-600 max-w-2xl">
        A supply-chain simulation for managing one vending machine and its local
        stockroom. Configure parameters, run simulations with baseline or
        student agents, and view daily performance charts.
      </p>

      <div className="grid sm:grid-cols-2 gap-6 max-w-2xl">
        <Link
          href="/configure"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-400 transition-colors"
        >
          <h2 className="font-semibold text-lg mb-2">1. Configure</h2>
          <p className="text-sm text-gray-500">
            Set simulation parameters: horizon, costs, and constraints.
          </p>
        </Link>
        <Link
          href="/run"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-400 transition-colors"
        >
          <h2 className="font-semibold text-lg mb-2">2. Run Simulation</h2>
          <p className="text-sm text-gray-500">
            Choose agents, pick a scenario, run, and explore charts.
          </p>
        </Link>
      </div>

      <div className="prose prose-sm max-w-2xl text-gray-600">
        <h3 className="text-lg font-semibold text-gray-800">Student agents</h3>
        <p>Each file must define one class:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <code>student_procurement.py</code> &rarr;{" "}
            <code>StudentProcurementAgent</code> with{" "}
            <code>act(self, obs: dict) -&gt; dict</code>
          </li>
          <li>
            <code>student_replenishment.py</code> &rarr;{" "}
            <code>StudentReplenishmentAgent</code> with{" "}
            <code>act(self, obs: dict) -&gt; dict</code>
          </li>
        </ul>
        <p>
          You can upload <code>.py</code> files or paste code directly on the
          Run page.
        </p>
      </div>
    </div>
  );
}
