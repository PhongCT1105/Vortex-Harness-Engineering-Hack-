"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  CaretDown,
  CheckCircle,
  Gauge,
  ListChecks,
  Robot,
  ShieldWarning,
  Sparkle,
  Clock,
  ChatCircleText,
  Cube,
  Plugs,
} from "@phosphor-icons/react/dist/ssr";
import {
  Action,
  AgentEventRow,
  Incident,
  IntegrationStatus,
  SupplyChainWeather,
  approveAction,
  getConfig,
  getEvents,
  getSupplyChainWeather,
  runIncident,
} from "@/lib/api";
import { AgentOutputPanel } from "@/components/AgentOutputPanel";
import { ConsoleShell } from "@/components/console/ConsoleShell";
import { StatCards } from "@/components/console/StatCards";
import { PipelineFlow } from "@/components/console/PipelineFlow";
import { IntegrationsPanel } from "@/components/console/IntegrationsPanel";
import { PromptChatPanel } from "@/components/console/PromptChatPanel";

const DEFAULT_EVENT = "A massive storm front is hitting Central Europe.";
const AUTO_REFRESH_MS = 4 * 60 * 60 * 1000; // 4 hours

const SCENARIOS = [
  "A massive storm front is hitting Central Europe.",
  "Flash flooding has shut down major highways across the Netherlands.",
  "A cold snap with heavy snowfall is sweeping through Poland and Sweden.",
];

const STEPS = [
  { href: "#trigger", label: "1. Trigger", icon: Sparkle },
  { href: "#assessment", label: "2. Weather & impact", icon: Gauge },
  { href: "#pipeline", label: "3. Pipeline & reasoning", icon: Cube },
  { href: "#actions", label: "4. Actions & approvals", icon: ShieldWarning },
  { href: "#ask", label: "5. Ask incident", icon: ChatCircleText },
  { href: "#audit", label: "6. Audit & integrations", icon: Plugs },
] as const;

export default function ConsolePage() {
  const [eventText, setEventText] = useState(DEFAULT_EVENT);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AgentEventRow[]>([]);
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [supplyWeather, setSupplyWeather] = useState<SupplyChainWeather | null>(null);
  const [supplyWeatherLoading, setSupplyWeatherLoading] = useState(false);
  const [lastRunAt, setLastRunAt] = useState<Date | null>(null);
  const [autoOpen, setAutoOpen] = useState(false);

  useEffect(() => {
    const poll = () => getEvents().then(setLogs).catch(() => {});
    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    getConfig().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    loadSupplyWeather(false);
  }, []);

  // Kick off the full end-to-end pipeline once on load, then every 4 hours.
  useEffect(() => {
    handleRun();
    const id = setInterval(handleRun, AUTO_REFRESH_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadSupplyWeather(forceRefresh: boolean) {
    setSupplyWeatherLoading(true);
    try {
      const result = await getSupplyChainWeather({ forceRefresh });
      setSupplyWeather(result);
    } catch {
      // non-fatal — supply weather is supplemental context
    } finally {
      setSupplyWeatherLoading(false);
    }
  }

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const result = await runIncident(eventText);
      setIncident(result);
      setLastRunAt(new Date());
      await Promise.all([
        getEvents().then(setLogs).catch(() => {}),
        loadSupplyWeather(true),
        getConfig().then(setStatus).catch(() => {}),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach backend");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(action: Action) {
    if (!incident) return;
    const result = await approveAction(action);
    const executed = { ...action, status: "approved", ...result };
    setIncident({
      ...incident,
      pending_approval: incident.pending_approval.filter((a) => a.id !== action.id),
      auto_executed: [...incident.auto_executed, executed],
    });
    getEvents().then(setLogs).catch(() => {});
  }

  const severe = incident?.weather.risk_level === "severe";
  const activeModel = status?.active_model ?? "claude";

  return (
    <ConsoleShell statusSlot={<ModelBadge model={activeModel} />}>
      <div className="flex flex-col gap-6">
        {/* Demo flow stepper */}
        <nav className="-mx-6 flex gap-2 overflow-x-auto px-6 pb-1 lg:-mx-10 lg:px-10">
          {STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <a
                key={step.href}
                href={step.href}
                className="flex shrink-0 items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-muted transition-colors hover:border-accent hover:text-text"
              >
                <Icon size={14} weight="bold" className="text-accent" />
                {step.label}
              </a>
            );
          })}
        </nav>

        {/* Pipeline trigger bar */}
        <motion.div
          id="trigger"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="scroll-mt-24 rounded-2xl border border-border bg-surface p-6"
        >
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Mission control</h1>
              <p className="mt-1 text-sm text-text-muted">
                Runs the full agent pipeline end-to-end — weather → impact → mitigation →
                reasoning → comms/Slack — and refreshes this dashboard and the audit trail.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-xs text-text-muted">
                <Clock size={14} weight="bold" />
                {lastRunAt
                  ? `Last run ${lastRunAt.toLocaleTimeString()}`
                  : loading
                    ? "Running…"
                    : "Not run yet"}
              </span>
              <button
                onClick={handleRun}
                disabled={loading}
                className="flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white transition-transform active:scale-[0.98] hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Spinner /> Running…
                  </>
                ) : (
                  <>
                    <Sparkle size={16} weight="bold" /> Run pipeline
                  </>
                )}
              </button>
            </div>
          </div>

          <p className="mt-2 text-xs text-text-muted">
            Auto-refreshes every 4 hours. The scenario below is the trigger event for the next
            run.
          </p>

          <textarea
            value={eventText}
            onChange={(e) => setEventText(e.target.value)}
            rows={2}
            className="mt-3 w-full resize-none rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm text-text outline-none transition-colors focus:border-accent"
          />

          <div className="mt-3 flex flex-wrap gap-2">
            {SCENARIOS.map((s) => (
              <button
                key={s}
                onClick={() => setEventText(s)}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                  eventText === s
                    ? "border-accent bg-accent-soft text-accent"
                    : "border-border text-text-muted hover:border-text-muted hover:text-text"
                }`}
              >
                {s.length > 42 ? s.slice(0, 42) + "…" : s}
              </button>
            ))}
          </div>

          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="mt-3 text-sm text-red-400"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>
        </motion.div>

        <StatCards incident={incident} />

        {!incident && !loading && (
          <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border bg-surface/40 px-6 py-16 text-center">
            <Robot size={28} weight="duotone" className="text-text-muted" />
            <p className="text-sm text-text-muted">
              Run the pipeline above to see weather risk, supplier impact, and proposed
              mitigations.
            </p>
          </div>
        )}

        <AnimatePresence mode="popLayout">
          {incident && (
            <motion.div
              key={incident.incident_id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col gap-6"
            >
              <div id="assessment" className="scroll-mt-24 grid gap-6 lg:grid-cols-2">
                {/* Left column: weather + impact */}
                <div className="flex flex-col gap-6">
                  <section
                    className={`rounded-2xl border p-6 transition-colors ${
                      severe ? "border-red-500/40 bg-red-500/[0.06]" : "border-border bg-surface"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <h2 className="flex items-center gap-2 text-lg font-semibold">
                        <Gauge size={20} weight="bold" className="text-accent" />
                        Weather assessment
                      </h2>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wide ${
                          severe ? "bg-red-500/20 text-red-300" : "bg-accent-soft text-accent"
                        }`}
                      >
                        {incident.weather.risk_level} · {incident.weather.source}
                      </span>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                      <Stat label="Affected" value={incident.weather.affected_countries.join(", ")} />
                      <Stat label="Wind" value={`${incident.weather.wind_kmh} km/h`} />
                      <Stat label="Precipitation" value={`${incident.weather.precipitation_mm} mm`} />
                      <Stat label="Severity" value={incident.weather.severity.toFixed(2)} />
                    </div>
                  </section>

                  <section className="rounded-2xl border border-border bg-surface p-6">
                    <h2 className="flex items-center gap-2 text-lg font-semibold">
                      <ListChecks size={20} weight="bold" className="text-accent" />
                      Impact
                    </h2>
                    <p className="mt-1 text-sm text-text-muted">
                      {incident.impact.affected_suppliers} suppliers ·{" "}
                      {incident.impact.at_risk_shipments} shipments at risk
                    </p>
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="text-text-muted">
                          <tr>
                            <th className="py-2 pr-4">Shipment</th>
                            <th className="py-2 pr-4">Component</th>
                            <th className="py-2 pr-4">Country</th>
                            <th className="py-2 pr-4">Value</th>
                            <th className="py-2 pr-4">Risk</th>
                          </tr>
                        </thead>
                        <tbody>
                          {incident.impact.shipments.map((s) => (
                            <tr key={s.shipment_id} className="border-t border-border">
                              <td className="py-2 pr-4 font-mono">{s.shipment_id}</td>
                              <td className="py-2 pr-4">{s.component}</td>
                              <td className="py-2 pr-4">{s.country}</td>
                              <td className="py-2 pr-4">${s.value_usd.toLocaleString()}</td>
                              <td className="py-2 pr-4">
                                <RiskPill score={s.risk_score} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </div>

                {/* Right column: pipeline */}
                <div id="pipeline" className="scroll-mt-24">
                  <PipelineFlow incident={incident} loading={loading} />
                </div>
              </div>

              <div id="actions" className="scroll-mt-24 grid gap-6 lg:grid-cols-2">
                {/* Left: agent reasoning */}
                <AgentOutputPanel logs={logs} model={activeModel} loading={loading} />

                {/* Right: actions & approvals */}
                <section className="rounded-2xl border border-border bg-surface p-6">
                  <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
                    <ShieldWarning size={20} weight="bold" className="text-accent" />
                    Actions & approvals
                  </h2>

                  <div className="flex flex-col gap-4">
                    {/* Pending approval — promoted to top */}
                    <div>
                      <p className="mb-2 text-sm font-medium text-text-muted">Pending approval</p>
                      {incident.pending_approval.length === 0 && (
                        <p className="text-sm text-text-muted">None.</p>
                      )}
                      <ul className="space-y-3">
                        <AnimatePresence>
                          {incident.pending_approval.map((a, i) => (
                            <motion.li
                              key={a.id}
                              initial={{ opacity: 0, x: -8 }}
                              animate={{ opacity: 1, x: 0 }}
                              exit={{ opacity: 0, scale: 0.97 }}
                              transition={{ delay: i * 0.05 }}
                              className="rounded-xl border border-border bg-surface-2 p-3 text-sm"
                            >
                              <p>{a.action}</p>
                              <div className="mt-2 flex items-center justify-between">
                                <span className="text-xs text-text-muted">
                                  ${a.value_usd.toLocaleString()} · risk {a.risk_score.toFixed(2)}
                                </span>
                                <button
                                  onClick={() => handleApprove(a)}
                                  className="rounded-full bg-accent px-3 py-1 text-xs font-medium text-white transition-transform active:scale-[0.97] hover:bg-accent/90"
                                >
                                  Approve
                                </button>
                              </div>
                            </motion.li>
                          ))}
                        </AnimatePresence>
                      </ul>
                    </div>

                    {/* Auto-executed — collapsible, collapsed by default */}
                    <div className="border-t border-border pt-4">
                      <button
                        onClick={() => setAutoOpen((o) => !o)}
                        className="flex w-full items-center justify-between text-left text-sm font-medium text-text-muted"
                      >
                        <span className="flex items-center gap-2">
                          <CheckCircle size={16} weight="bold" className="text-accent" />
                          Auto-executed ({incident.auto_executed.length})
                        </span>
                        <motion.span animate={{ rotate: autoOpen ? 180 : 0 }}>
                          <CaretDown size={16} weight="bold" />
                        </motion.span>
                      </button>
                      <AnimatePresence initial={false}>
                        {autoOpen && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                            className="overflow-hidden"
                          >
                            <div className="mt-3">
                              {incident.auto_executed.length === 0 && (
                                <p className="text-sm text-text-muted">None yet.</p>
                              )}
                              <ul className="space-y-3">
                                {incident.auto_executed.map((a, i) => (
                                  <motion.li
                                    key={a.id}
                                    initial={{ opacity: 0, x: -8 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.05 }}
                                    className="rounded-xl border border-border bg-surface-2 p-3 text-sm"
                                  >
                                    <p>{a.action}</p>
                                    <p className="mt-1 text-xs text-text-muted">
                                      ${a.value_usd.toLocaleString()} · risk {a.risk_score.toFixed(2)} ·{" "}
                                      {a.sent ? "sent" : "logged (mock)"}
                                    </p>
                                  </motion.li>
                                ))}
                              </ul>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </section>
              </div>

              <div id="ask" className="scroll-mt-24">
                <PromptChatPanel incident={incident} logs={logs} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div id="audit" className="scroll-mt-24 flex flex-col gap-6">
          <AuditLog logs={logs} />

          {supplyWeather && (
            <SupplyWeatherSummary weather={supplyWeather} loading={supplyWeatherLoading} />
          )}

          <IntegrationsPanel status={status} setStatus={setStatus} />
        </div>
      </div>
    </ConsoleShell>
  );
}

function SupplyWeatherSummary({
  weather,
  loading,
}: {
  weather: SupplyChainWeather;
  loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const generated = new Date(weather.generated_at).toLocaleString();

  return (
    <section className="rounded-2xl border border-border bg-surface p-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left"
      >
        <div>
          <h2 className="text-lg font-semibold">Supply-chain weather intelligence</h2>
          <p className="mt-1 text-sm text-text-muted">
            {weather.countries.length} countries monitored · worst level{" "}
            <RiskLevelPill level={weather.worst_risk_level} /> · generated {generated}
            {loading && " · refreshing…"}
          </p>
        </div>
        <motion.span animate={{ rotate: open ? 180 : 0 }} className="text-text-muted">
          <CaretDown size={18} weight="bold" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-4 grid gap-3">
              {weather.countries.map((country) => (
                <article key={country.country} className="rounded-xl border border-border bg-surface-2 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold">{country.country}</h3>
                    <RiskLevelPill level={country.risk_level} />
                    <span className="font-mono text-xs text-text-muted">
                      {country.wind_kmh} km/h · {country.precipitation_mm} mm · score{" "}
                      {country.severity.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-text-muted">{country.context}</p>
                </article>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function Spinner() {
  return (
    <motion.span
      animate={{ rotate: 360 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
      className="block h-3.5 w-3.5 rounded-full border-2 border-white/30 border-t-white"
    />
  );
}

function RiskLevelPill({ level }: { level: "normal" | "watch" | "high" | "severe" }) {
  const color =
    level === "severe"
      ? "bg-red-500/20 text-red-300"
      : level === "high"
        ? "bg-amber-500/20 text-amber-300"
        : level === "watch"
          ? "bg-sky-500/20 text-sky-300"
          : "bg-accent-soft text-accent";
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium uppercase tracking-wide ${color}`}>
      {level}
    </span>
  );
}

function ModelBadge({ model }: { model: "claude" | "deepseek" }) {
  const label = model === "claude" ? "Claude" : "DeepSeek";
  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-xs font-medium text-text-muted">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
      </span>
      Reasoning agent · <span className="text-text">{label}</span>
    </div>
  );
}

function RiskPill({ score }: { score: number }) {
  const high = score >= 0.7;
  const mid = score >= 0.5;
  const color = high
    ? "bg-red-500/20 text-red-300"
    : mid
      ? "bg-amber-500/20 text-amber-300"
      : "bg-accent-soft text-accent";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      {score.toFixed(2)}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function AuditLog({ logs }: { logs: AgentEventRow[] }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="rounded-2xl border border-border bg-surface p-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left"
      >
        <h2 className="text-lg font-semibold">Audit log</h2>
        <motion.span animate={{ rotate: open ? 180 : 0 }} className="text-text-muted">
          <CaretDown size={18} weight="bold" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-4">
              {logs.length === 0 && <p className="text-sm text-text-muted">No events yet.</p>}
              <ul className="max-h-72 space-y-1 overflow-y-auto font-mono text-xs text-text-muted">
                {logs
                  .slice()
                  .reverse()
                  .slice(0, 30)
                  .map((log, i) => (
                    <li key={i} className="border-t border-border py-1.5 first:border-t-0">
                      <span className="text-text">{new Date(log.ts * 1000).toLocaleTimeString()}</span>{" "}
                      · {log.incident_id} · <span className="text-accent">{log.kind}</span>
                    </li>
                  ))}
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
