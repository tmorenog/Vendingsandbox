import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "VendSim -- Vending Machine Sandbox",
  description: "Supply-chain simulation for vending machine operations",
};

function Navbar() {
  const links = [
    { href: "/", label: "Home" },
    { href: "/configure", label: "Configure" },
    { href: "/run", label: "Run Simulation" },
  ];
  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-14 gap-8">
        <span className="font-bold text-lg tracking-tight">VendSim</span>
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
