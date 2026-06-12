"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowLeft,
  CloudLightning,
  Factory,
  Globe as GlobeIcon,
  MapPin,
  Sparkle,
  UploadSimple,
} from "@phosphor-icons/react/dist/ssr";
import {
  SupplyChain,
  SupplyChainAutomationResult,
  SupplyChainNode,
  getSupplyChain,
  runSupplyChainAutomation,
  uploadSupplyChain,
} from "@/lib/api";
import { SupplyChainGlobe } from "@/components/supply-chain/SupplyChainGlobe";

const SAMPLE_CSV = `supplier_id,country,component,value_usd,criticality
S1,Germany,Steel chassis,150000,0.9
S2,Austria,Aluminum frame,80000,0.7
S3,Poland,Wiring harness,45000,0.5
S4,Spain,Glass panels,120000,0.85
S5,Netherlands,Hydraulic pumps,60000,0.6
S6,Sweden,Bearings,30000,0.4
S7,Germany,Control units,95000,0.75
S8,Poland,Tires,25000,0.3`;

export default function SupplyChainPage() {
  const [product, setProduct] = useState("Electric Vehicle");
  const [data, setData] = useState<SupplyChain | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [automation, setAutomation] = useState<SupplyChainAutomationResult | null>(null);
  const [automationError, setAutomationError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SupplyChainNode | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDefault = useCallback(async (productName: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getSupplyChain(productName);
      setData(result);
      setSelected(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach backend");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
    void loadDefault(product);
  }, []);

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    setAutomationError(null);
    try {
      const result = await uploadSupplyChain(file, product || "Product");
      setData(result);
      setSelected(null);
      try {
        const automationResult = await runSupplyChainAutomation({
          product: result.product,
          forceRefresh: false,
        });
        setAutomation(automationResult);
      } catch (automationErr) {
        setAutomationError(
          automationErr instanceof Error ? automationErr.message : "Failed to run automation"
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload supply chain");
    } finally {
      setLoading(false);
    }
  }

  function downloadSample() {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample-supply-chain.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg">
      {/* Top bar */}
      <header className="flex shrink-0 items-center justify-between border-b border-border bg-bg/80 px-6 py-4 backdrop-blur-md lg:px-10">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-text-muted transition-colors hover:text-text"
          >
            <ArrowLeft size={16} weight="bold" />
            Back
          </Link>
          <span className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2 font-semibold tracking-tight">
            <CloudLightning size={20} weight="duotone" className="text-accent" />
            StormOps
          </div>
        </div>
        <Link
          href="/console"
          className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-transform active:scale-[0.98] hover:bg-accent/90"
        >
          Open console
        </Link>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[22rem_1fr]">
        {/* Sidebar / control panel */}
        <aside className="flex min-h-0 flex-col gap-6 overflow-y-auto border-b border-border bg-surface/60 px-6 py-6 lg:border-b-0 lg:border-r">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-accent">
              <GlobeIcon size={14} weight="bold" />
              Step 1 · Map your supply chain
            </div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              Where does your product come from?
            </h1>
            <p className="mt-2 text-sm text-text-muted">
              Upload a CSV of your suppliers — country, component, value, and
              criticality — and watch every resource flow onto the globe
              toward your assembly plant.
            </p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-text-muted">
              Product name
            </label>
            <input
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              onBlur={() => loadDefault(product)}
              placeholder="e.g. Electric Vehicle"
              className="w-full rounded-xl border border-border bg-surface-2 px-4 py-2.5 text-sm text-text outline-none transition-colors focus:border-accent"
            />
          </div>

          <div className="flex flex-col gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-surface-2 px-4 py-6 text-sm text-text-muted transition-colors hover:border-accent hover:text-accent"
            >
              <UploadSimple size={18} weight="bold" />
              Upload supply chain CSV
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = "";
              }}
            />
            <div className="flex items-center justify-between text-xs text-text-muted">
              <span>Columns: supplier_id, country, component, value_usd, criticality</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={downloadSample}
                className="flex-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-text-muted transition-colors hover:border-text-muted hover:text-text"
              >
                Download sample CSV
              </button>
              <button
                onClick={() => loadDefault(product)}
                className="flex items-center gap-1.5 flex-1 justify-center rounded-full bg-accent px-3 py-1.5 text-xs font-medium text-white transition-transform active:scale-[0.97] hover:bg-accent/90"
              >
                <Sparkle size={14} weight="bold" />
                Load demo data
              </button>
            </div>
          </div>

          {error && (
            <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              {error}
            </p>
          )}

          {automationError && (
            <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              Map loaded, but automation failed: {automationError}
            </p>
          )}

          {data && (
            <>
              {automation && (
                <div className="rounded-xl border border-border bg-surface-2 px-3 py-3 text-xs text-text-muted">
                  <p className="font-medium text-text">Automation report generated</p>
                  <p className="mt-1">{automation.report.executive_summary}</p>
                  <p className="mt-2">
                    Source: {automation.weather_source === "clickhouse_cached" ? "ClickHouse cached weather" : "fresh weather refresh"} · Slack{" "}
                    {automation.dispatch.slack.sent ? "sent" : automation.dispatch.slack.configured ? "failed" : "mock"}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <StatCard label="Resources" value={data.nodes.length.toString()} />
                <StatCard
                  label="Total value"
                  value={`$${(data.total_value_usd / 1000).toFixed(0)}k`}
                />
                <StatCard
                  label="Countries"
                  value={new Set(data.nodes.map((n) => n.country)).size.toString()}
                />
                <StatCard label="Assembly" value={data.assembly.city} />
              </div>

              <div>
                <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-text">
                  <Factory size={16} weight="bold" className="text-accent" />
                  Resource flows → {data.assembly.name}
                </h2>
                <ul className="flex flex-col gap-2">
                  {data.nodes.map((node, i) => (
                    <motion.li
                      key={node.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.04 }}
                    >
                      <button
                        onClick={() => setSelected(node)}
                        className={`flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition-colors ${
                          selected?.id === node.id
                            ? "border-accent bg-accent-soft text-accent"
                            : "border-border bg-surface-2 text-text hover:border-text-muted"
                        }`}
                      >
                        <span className="flex items-center gap-2 truncate">
                          <MapPin size={14} weight="bold" className="shrink-0 text-text-muted" />
                          <span className="truncate">
                            <span className="font-medium">{node.component}</span>
                            <span className="text-text-muted"> · {node.country}</span>
                          </span>
                        </span>
                        <span className="shrink-0 pl-2 text-xs text-text-muted">
                          ${(node.value_usd / 1000).toFixed(0)}k
                        </span>
                      </button>
                    </motion.li>
                  ))}
                </ul>
              </div>

              {data.unresolved_countries.length > 0 && (
                <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                  Could not place: {data.unresolved_countries.join(", ")}
                </p>
              )}
            </>
          )}
        </aside>

        {/* Globe */}
        <main className="relative min-h-0">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/60 backdrop-blur-sm">
              <Spinner />
            </div>
          )}
          {data && <SupplyChainGlobe data={data} onSelectNode={setSelected} />}

          {/* Title overlay */}
          <div className="pointer-events-none absolute left-6 top-6 max-w-sm">
            <p className="text-xs font-medium uppercase tracking-wider text-accent">
              {data?.product ?? "Product"}
            </p>
            <h2 className="mt-1 text-3xl font-semibold tracking-tight text-text drop-shadow-lg">
              Global supply chain
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              {data ? `${data.nodes.length} sources → ${data.assembly.city}, ${data.assembly.country}` : ""}
            </p>
          </div>

          {/* Selected node card */}
          <AnimatePresence>
            {selected && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 16 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                className="absolute bottom-6 left-6 right-6 max-w-md rounded-2xl border border-border bg-surface/90 p-5 backdrop-blur-md sm:right-auto"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">{selected.component}</h3>
                  <button
                    onClick={() => setSelected(null)}
                    className="text-text-muted transition-colors hover:text-text"
                  >
                    ✕
                  </button>
                </div>
                <p className="mt-1 text-sm text-text-muted">
                  Sourced from <span className="text-text">{selected.country}</span> → shipped to{" "}
                  <span className="text-text">{data?.assembly.city}</span>
                </p>
                <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                  <Stat label="Value" value={`$${selected.value_usd.toLocaleString()}`} />
                  <Stat label="Criticality" value={selected.criticality.toFixed(2)} />
                  <Stat label="Node" value={selected.id} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-2 px-3 py-2.5">
      <p className="text-[10px] uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-0.5 font-medium">{value}</p>
    </div>
  );
}

function Spinner() {
  return (
    <motion.span
      animate={{ rotate: 360 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
      className="block h-8 w-8 rounded-full border-2 border-white/20 border-t-accent"
    />
  );
}
