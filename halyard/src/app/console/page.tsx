"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  CaretDown,
  CheckCircle,
  Gauge,
  ArrowClockwise,
  ListChecks,
  Robot,
  ShieldWarning,
  Sparkle,
} from "@phosphor-icons/react/dist/ssr";
import {
  Action,
  AgentEventRow,
  Incident,
  IntegrationStatus,
  SupplyChainAutomationResult,
  SupplyChainWeather,
  approveAction,
  getConfig,
  getEvents,
  getSupplyChainWeather,
  runIncident,
  runSupplyChainAutomation,
} from "@/lib/api";
import { AgentOutputPanel } from "@/components/AgentOutputPanel";
import { ConsoleShell, TabKey } from "@/components/console/ConsoleShell";
import { StatCards } from "@/components/console/StatCards";
import { PipelineFlow } from "@/components/console/PipelineFlow";
import { IntegrationsPanel } from "@/components/console/IntegrationsPanel";
import { PromptChatPanel } from "@/components/console/PromptChatPanel";

const DEFAULT_EVENT = "A massive storm front is hitting Central Europe.";

const SCENARIOS = [
  "A massive storm front is hitting Central Europe.",
  "Flash flooding has shut down major highways across the Netherlands.",
  "A cold snap with heavy snowfall is sweeping through Poland and Sweden.",
];

export default function ConsolePage() {
  const [eventText, setEventText] = useState(DEFAULT_EVENT);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AgentEventRow[]>([]);
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [supplyWeather, setSupplyWeather] = useState<SupplyChainWeather | null>(null);
  const [supplyWeatherLoading, setSupplyWeatherLoading] = useState(false);
  const [supplyWeatherError, setSupplyWeatherError] = useState<string | null>(null);
  const [automation, setAutomation] = useState<SupplyChainAutomationResult | null>(null);
  const [automationLoading, setAutomationLoading] = useState(false);
  const [automationError, setAutomationError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("overview");

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

  async function loadSupplyWeather(forceRefresh: boolean) {
    setSupplyWeatherLoading(true);
    setSupplyWeatherError(null);
    try {
      const result = await getSupplyChainWeather({ forceRefresh });
      setSupplyWeather(result);
    } catch (err) {
      setSupplyWeatherError(err instanceof Error ? err.message : "Failed to fetch supply-chain weather");
    } finally {
      setSupplyWeatherLoading(false);
    }
  }

  async function handleSupplyAutomation(forceRefresh: boolean) {
    setAutomationLoading(true);
    setAutomationError(null);
    try {
      const result = await runSupplyChainAutomation({ forceRefresh });
      setAutomation(result);
      const latestWeather = await getSupplyChainWeather({ forceRefresh: false });
      setSupplyWeather(latestWeather);
      getEvents().then(setLogs).catch(() => {});
    } catch (err) {
      setAutomationError(err instanceof Error ? err.message : "Failed to run automation");
    } finally {
      setAutomationLoading(false);
    }
  }

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const result = await runIncident(eventText);
      setIncident(result);
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
    <ConsoleShell active={tab} onChange={setTab} statusSlot={<ModelBadge model={activeModel} />}>
      {/* Overview */}
      {tab === "overview" && (
      <section className="flex flex-col gap-6">
        <StatCards incident={incident} />

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-2xl border border-border bg-surface p-6"
        >
          <label className="mb-2 block text-sm font-medium text-text-muted">
            Scenario / trigger event
          </label>
          <textarea
            value={eventText}
            onChange={(e) => setEventText(e.target.value)}
            rows={2}
            className="w-full resize-none rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm text-text outline-none transition-colors focus:border-accent"
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

          <div className="mt-4 flex items-center gap-3">
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
                  <Sparkle size={16} weight="bold" /> Run scenario
                </>
              )}
            </button>
            <AnimatePresence>
              {error && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-sm text-red-400"
                >
                  {error}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

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
              {/* Weather */}
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
                      severe
                        ? "bg-red-500/20 text-red-300"
                        : "bg-accent-soft text-accent"
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

              {/* Impact */}
              <section className="rounded-2xl border border-border bg-surface p-6">
                <h2 className="flex items-center gap-2 text-lg font-semibold">
                  <ListChecks size={20} weight="bold" className="text-accent" />
                  Impact — {incident.impact.affected_suppliers} suppliers,{" "}
                  {incident.impact.at_risk_shipments} shipments at risk
                </h2>
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
            </motion.div>
          )}
        </AnimatePresence>

        {!incident && !loading && (
          <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border bg-surface/40 px-6 py-16 text-center">
            <Robot size={28} weight="duotone" className="text-text-muted" />
            <p className="text-sm text-text-muted">
              Run a scenario above to see weather risk, supplier impact, and
              proposed mitigations.
            </p>
          </div>
        )}
      </section>
      )}

      {/* Pipeline */}
      {tab === "pipeline" && (
      <section className="flex flex-col gap-6">
        <PipelineFlow incident={incident} loading={loading} />
      </section>
      )}

      {/* Supply weather */}
      {tab === "supply-weather" && (
      <SupplyWeatherPanel
        weather={supplyWeather}
        loading={supplyWeatherLoading}
        error={supplyWeatherError}
        onRefresh={() => loadSupplyWeather(true)}
        automation={automation}
        automationLoading={automationLoading}
        automationError={automationError}
        onAutomate={(forceRefresh) => handleSupplyAutomation(forceRefresh)}
      />
      )}

      {/* Agent reasoning */}
      {tab === "reasoning" && (
      <section>
        <AgentOutputPanel logs={logs} model={activeModel} loading={loading} />
      </section>
      )}

      {/* Prompt chat */}
      {tab === "ask" && (
      <PromptChatPanel incident={incident} logs={logs} />
      )}

      {/* Actions & approvals */}
      {tab === "actions" && (
      <section className="grid gap-6 sm:grid-cols-2">
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <CheckCircle size={20} weight="bold" className="text-accent" />
            Auto-executed
          </h2>
          {(!incident || incident.auto_executed.length === 0) && (
            <p className="text-sm text-text-muted">None yet.</p>
          )}
          <ul className="space-y-3">
            {incident?.auto_executed.map((a, i) => (
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

        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <ShieldWarning size={20} weight="bold" className="text-accent" />
            Pending approval
          </h2>
          {(!incident || incident.pending_approval.length === 0) && (
            <p className="text-sm text-text-muted">None.</p>
          )}
          <ul className="space-y-3">
            <AnimatePresence>
              {incident?.pending_approval.map((a, i) => (
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
      </section>
      )}

      {/* Audit log */}
      {tab === "audit" && (
      <section>
        <AuditLog logs={logs} />
      </section>
      )}

      {/* Integrations */}
      {tab === "integrations" && (
      <section>
        <IntegrationsPanel status={status} setStatus={setStatus} />
      </section>
      )}
    </ConsoleShell>
  );
}

function SupplyWeatherPanel({
  weather,
  loading,
  error,
  onRefresh,
  automation,
  automationLoading,
  automationError,
  onAutomate,
}: {
  weather: SupplyChainWeather | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  automation: SupplyChainAutomationResult | null;
  automationLoading: boolean;
  automationError: string | null;
  onAutomate: (forceRefresh: boolean) => void;
}) {
  const generated = weather ? new Date(weather.generated_at).toLocaleString() : "Not loaded";
  const expires = weather ? new Date(weather.expires_at).toLocaleString() : "Not loaded";

  return (
    <section className="flex flex-col gap-6">
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Supply-chain weather intelligence</h2>
            <p className="mt-1 text-sm text-text-muted">
              Open-Meteo numeric risk plus search context, refreshed every{" "}
              {weather ? Math.round(weather.refresh_seconds / 3600) : 4} hours.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="flex w-fit items-center gap-2 rounded-full border border-border bg-surface-2 px-4 py-2 text-sm font-medium text-text transition-colors hover:border-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Spinner /> : <ArrowClockwise size={16} weight="bold" />}
              Refresh
            </button>
            <button
              onClick={() => onAutomate(false)}
              disabled={automationLoading}
              className="flex w-fit items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {automationLoading ? <Spinner /> : <Sparkle size={16} weight="bold" />}
              Run automation
            </button>
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
        {automationError && <p className="mt-4 text-sm text-red-400">{automationError}</p>}

        <div className="mt-5 grid gap-4 text-sm sm:grid-cols-4">
          <Stat label="Worst level" value={weather?.worst_risk_level ?? "Loading"} />
          <Stat label="Max severity" value={weather ? weather.max_severity.toFixed(2) : "..."} />
          <Stat label="Generated" value={generated} />
          <Stat label="Next refresh" value={expires} />
        </div>
      </div>

      {automation && (
        <div className="rounded-2xl border border-border bg-surface p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="text-base font-semibold">Automation report</h3>
              <p className="mt-1 text-sm text-text-muted">{automation.report.executive_summary}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <RiskLevelPill level={automation.report.current_condition} />
              <span className="rounded-full border border-border px-2.5 py-1 text-xs text-text-muted">
                {automation.weather_source === "clickhouse_cached" ? "ClickHouse cached" : "Refreshed"}
              </span>
              <span className="rounded-full border border-border px-2.5 py-1 text-xs text-text-muted">
                Slack {automation.dispatch.slack.sent ? "sent" : automation.dispatch.slack.configured ? "failed" : "mock"}
              </span>
              <span className="rounded-full border border-border px-2.5 py-1 text-xs text-text-muted">
                Airbyte {automation.dispatch.airbyte.sent ? "sent" : automation.dispatch.airbyte.configured ? "configured" : "off"}
              </span>
            </div>
          </div>
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface-2 p-3">
              <p className="text-xs uppercase tracking-wide text-text-muted">Recommended actions</p>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {automation.report.recommended_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 p-3">
              <p className="text-xs uppercase tracking-wide text-text-muted">Exposure summary</p>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {automation.report.exposure_summary.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {!weather && !error && (
        <div className="rounded-2xl border border-dashed border-border bg-surface/40 p-8 text-sm text-text-muted">
          {loading ? "Fetching supply-chain weather..." : "No weather intelligence loaded yet."}
        </div>
      )}

      {weather && (
        <div className="grid gap-4">
          {weather.routes.length > 0 && (
            <div className="rounded-2xl border border-border bg-surface p-5">
              <h3 className="text-base font-semibold">Route risk lanes</h3>
              <div className="mt-3 grid gap-2">
                {weather.routes.slice(0, 6).map((route) => (
                  <div
                    key={route.supplier_id}
                    className="rounded-xl border border-border bg-surface-2 p-3 text-sm"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-medium">
                          {route.component} · {route.country} → {route.destination.city}
                        </p>
                        <p className="mt-0.5 text-xs text-text-muted">{route.context}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <RiskLevelPill level={route.worst_risk_level} />
                        <span className="font-mono text-xs text-text-muted">
                          {route.max_severity.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {weather.countries.map((country) => (
            <article key={country.country} className="rounded-2xl border border-border bg-surface p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold">{country.country}</h3>
                    <RiskLevelPill level={country.risk_level} />
                  </div>
                  <p className="mt-2 max-w-4xl text-sm text-text-muted">{country.context}</p>
                </div>
                <div className="grid min-w-64 grid-cols-3 gap-2 text-right text-sm">
                  <MiniMetric label="Wind" value={`${country.wind_kmh} km/h`} />
                  <MiniMetric label="Rain" value={`${country.precipitation_mm} mm`} />
                  <MiniMetric label="Score" value={country.severity.toFixed(2)} />
                </div>
              </div>

              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-[1fr_1.4fr]">
                <div className="rounded-xl border border-border bg-surface-2 p-3">
                  <p className="text-xs uppercase tracking-wide text-text-muted">Supply exposure</p>
                  <p className="mt-1 font-medium">
                    {country.supplier_count} supplier{country.supplier_count === 1 ? "" : "s"} · $
                    {country.value_usd.toLocaleString()}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    Avg criticality {country.avg_criticality.toFixed(2)} · {country.components.join(", ")}
                  </p>
                </div>

                <div className="rounded-xl border border-border bg-surface-2 p-3">
                  <p className="text-xs uppercase tracking-wide text-text-muted">
                    Context · {country.search.source}
                  </p>
                  <p className="mt-1 text-sm">{country.search.summary}</p>
                  {country.search.results.length > 0 && (
                    <ul className="mt-2 space-y-2">
                      {country.search.results.slice(0, 2).map((result) => (
                        <li key={result.url}>
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sm font-medium text-accent hover:underline"
                          >
                            {result.title}
                          </a>
                          {result.snippet && (
                            <p className="mt-0.5 line-clamp-2 text-xs text-text-muted">
                              {result.snippet}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
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

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
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
