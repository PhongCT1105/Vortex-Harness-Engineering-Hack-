"use client";

import { FormEvent, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { motion } from "motion/react";
import {
  ArrowRight,
  ChatCircleText,
  CheckCircle,
  Factory,
  GitBranch,
  Lightning,
  PaperPlaneTilt,
  ShieldWarning,
  WarningDiamond,
} from "@phosphor-icons/react/dist/ssr";
import { AgentEventRow, Incident, IncidentChatResponse, askIncident } from "@/lib/api";

type ChatMessage = {
  role: "operator" | "orchestrator";
  content: string;
  openuiLang?: string;
};

const DEFAULT_QUESTIONS = [
  "Which part of the supply chain is damaged?",
  "Why did Jua classify this as high risk?",
  "Which mitigations need approval?",
  "Show the ClickHouse audit trail.",
];

export function PromptChatPanel({
  incident,
  logs,
}: {
  incident: Incident | null;
  logs: AgentEventRow[];
}) {
  const [question, setQuestion] = useState(DEFAULT_QUESTIONS[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastResponse, setLastResponse] = useState<IncidentChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const incidentLogs = useMemo(
    () => logs.filter((log) => log.incident_id === incident?.incident_id),
    [incident?.incident_id, logs],
  );

  async function submitPrompt(nextQuestion = question) {
    if (!incident || loading || !nextQuestion.trim()) return;
    setLoading(true);
    setError(null);
    setQuestion("");
    setMessages((current) => [...current, { role: "operator", content: nextQuestion }]);

    try {
      const response = await askIncident(nextQuestion, incident);
      setLastResponse(response);
      setMessages((current) => [
        ...current,
        {
          role: "orchestrator",
          content: response.answer,
          openuiLang: response.openui_lang,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ask incident");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submitPrompt();
  }

  if (!incident) {
    return (
      <section className="rounded-2xl border border-dashed border-border bg-surface/50 p-8 text-center">
        <ChatCircleText size={28} weight="duotone" className="mx-auto text-text-muted" />
        <p className="mt-3 text-sm text-text-muted">
          Run a scenario first, then ask the orchestration layer about the returned Jua,
          ClickHouse, impact, and mitigation data.
        </p>
      </section>
    );
  }

  const suggested =
    lastResponse?.suggested_questions ??
    incident.orchestration?.operator_questions ??
    DEFAULT_QUESTIONS;

  return (
    <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(22rem,0.9fr)]">
      <div className="rounded-2xl border border-border bg-surface p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-accent">
              Operator prompt window
            </p>
            <h2 className="mt-1 text-lg font-semibold">Ask about this incident</h2>
          </div>
          <span className="rounded-full border border-border bg-surface-2 px-3 py-1 text-xs text-text-muted">
            {incident.weather.source} + {incidentLogs.length} audit events
          </span>
        </div>

        <div className="mt-5 max-h-[32rem] space-y-3 overflow-y-auto rounded-xl border border-border bg-bg/45 p-3">
          {messages.length === 0 && (
            <div className="rounded-xl border border-border bg-surface/80 p-4 text-sm text-text-muted">
              Ask a follow-up like “which component is damaged?” The answer is grounded
              in the incident payload and the ClickHouse/audit timeline.
              {incident.orchestration?.executive_summary && (
                <p className="mt-2 text-text">
                  {incident.orchestration.executive_summary}
                </p>
              )}
            </div>
          )}
          {messages.map((message, index) => (
            <motion.div
              key={`${message.role}-${index}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`rounded-xl border p-3 text-sm ${
                message.role === "operator"
                  ? "ml-auto max-w-[86%] border-accent/30 bg-accent-soft text-text"
                  : "mr-auto max-w-[92%] border-border bg-surface-2 text-text"
              }`}
            >
              <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                {message.role === "operator" ? "Operator" : "Orchestrator"}
              </p>
              <p className="mt-1 leading-6">{message.content}</p>
              {message.openuiLang && <OpenUILangBlock source={message.openuiLang} />}
            </motion.div>
          ))}
          {loading && (
            <div className="mr-auto rounded-xl border border-border bg-surface-2 p-3 text-sm text-text-muted">
              Building incident answer…
            </div>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {suggested.map((item) => (
            <button
              key={item}
              onClick={() => void submitPrompt(item)}
              disabled={loading}
              className="rounded-full border border-border px-3 py-1 text-xs text-text-muted transition-colors hover:border-accent hover:text-text disabled:opacity-50"
            >
              {item}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask what was damaged, why, or what to approve..."
            className="min-w-0 flex-1 rounded-full border border-border bg-surface-2 px-4 py-2.5 text-sm text-text outline-none transition-colors focus:border-accent"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="flex items-center gap-2 rounded-full bg-accent px-4 py-2.5 text-sm font-medium text-white transition-transform hover:bg-accent/90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PaperPlaneTilt size={16} weight="bold" />
            Ask
          </button>
        </form>
        {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      </div>

      <SupplyChainSimulation incident={incident} auditCount={incidentLogs.length} />
    </section>
  );
}

function SupplyChainSimulation({
  incident,
  auditCount,
}: {
  incident: Incident;
  auditCount: number;
}) {
  const topShipments = incident.impact.shipments.slice(0, 3);
  const approvalCount = incident.pending_approval.length;
  const autoCount = incident.auto_executed.length;
  const totalValueAtRisk = incident.impact.shipments.reduce((sum, s) => sum + s.value_usd, 0);
  const severityPct = Math.round(Math.min(1, incident.weather.severity) * 100);
  const confidencePct = Math.round((incident.orchestration?.confidence ?? 0) * 100);
  const priorityOrder = incident.orchestration?.priority_order ?? [];
  const damagedNodes = incident.orchestration?.damaged_nodes ?? [];

  return (
    <aside className="relative overflow-hidden rounded-2xl border border-border bg-surface p-5">
      <div className="pointer-events-none absolute -right-24 -top-24 h-56 w-56 rounded-full bg-red-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 -left-20 h-48 w-48 rounded-full bg-accent/10 blur-3xl" />

      <div className="relative flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-accent">
            OpenUI incident visualization
          </p>
          <h2 className="mt-1 text-lg font-semibold">Supply-chain damage map</h2>
        </div>
        {incident.orchestration && (
          <span className="shrink-0 rounded-full border border-accent/30 bg-accent-soft px-3 py-1 text-[11px] font-medium text-accent">
            {incident.orchestration.source} · {confidencePct}% confidence
          </span>
        )}
      </div>

      <div className="relative mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Severity" value={`${severityPct}%`} tone="danger" />
        <StatTile label="Shipments at risk" value={incident.impact.at_risk_shipments} tone="warning" />
        <StatTile label="Value exposed" value={_money(totalValueAtRisk)} tone="warning" />
        <StatTile label="Audit events" value={auditCount} tone="recovering" />
      </div>

      <div className="relative mt-3 rounded-xl border border-red-500/20 bg-red-500/[0.06] p-3">
        <div className="flex items-center justify-between text-[11px] text-text-muted">
          <span className="font-medium uppercase tracking-wide text-red-300">Storm severity</span>
          <span>{severityPct}%</span>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-bg/60">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 via-orange-500 to-red-500"
            initial={{ width: 0 }}
            animate={{ width: `${severityPct}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </div>
      </div>

      <div className="relative mt-5 space-y-3">
        <ChainNode
          icon={<WarningDiamond size={18} weight="bold" />}
          title="Weather zone"
          detail={incident.weather.affected_countries.join(", ")}
          status={`${incident.weather.risk_level} · ${incident.weather.wind_kmh} km/h wind · ${incident.weather.precipitation_mm} mm rain`}
          tone="danger"
          pulse
        />
        <Connector damaged />
        <ChainNode
          icon={<GitBranch size={18} weight="bold" />}
          title="Supplier lane"
          detail={`${incident.impact.at_risk_shipments} shipments exposed`}
          status={topShipments.map((s) => s.component).join(", ") || "No damaged lane"}
          tone="warning"
          pulse
        />
        <Connector damaged={approvalCount > 0} />
        <ChainNode
          icon={<Factory size={18} weight="bold" />}
          title="Factory plan"
          detail={`${autoCount} auto actions · ${approvalCount} approval gates`}
          status={`${auditCount} ClickHouse/audit events captured`}
          tone="recovering"
        />
      </div>

      {damagedNodes.length > 0 && (
        <div className="relative mt-5">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            Damage assessment
          </p>
          <ul className="mt-2 space-y-2">
            {damagedNodes.map((node) => (
              <li
                key={node.node}
                className="flex items-start gap-2 rounded-lg border border-border bg-bg/45 px-3 py-2 text-sm"
              >
                <SeverityBadge severity={node.severity} />
                <span className="min-w-0">
                  <span className="block font-medium">{node.node}</span>
                  <span className="text-xs text-text-muted">{node.reason}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="relative mt-5 rounded-xl border border-border bg-bg/45 p-3">
        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
          Damaged components
        </p>
        <ul className="mt-2 space-y-2">
          {topShipments.length === 0 && (
            <li className="text-sm text-text-muted">No damaged components found.</li>
          )}
          {topShipments.map((shipment) => (
            <li
              key={shipment.shipment_id}
              className="rounded-lg bg-surface-2 px-3 py-2 text-sm"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="min-w-0">
                  <span className="block truncate font-medium">{shipment.component}</span>
                  <span className="text-xs text-text-muted">
                    {shipment.country} · {shipment.shipment_id} · {_money(shipment.value_usd)}
                  </span>
                </span>
                <span className="shrink-0 rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-300">
                  {shipment.risk_score.toFixed(2)}
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-bg/60">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-amber-400 to-red-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round(Math.min(1, shipment.risk_score) * 100)}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              </div>
            </li>
          ))}
        </ul>
      </div>

      {(incident.auto_executed.length > 0 || incident.pending_approval.length > 0) && (
        <div className="relative mt-5">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            Recovery plan
          </p>
          <ul className="mt-2 space-y-2">
            {incident.auto_executed.map((action) => (
              <li
                key={action.id}
                className="flex items-start gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.06] px-3 py-2 text-sm"
              >
                <CheckCircle size={16} weight="fill" className="mt-0.5 shrink-0 text-emerald-400" />
                <span className="min-w-0">
                  <span className="block font-medium text-emerald-200">{action.action}</span>
                  <span className="text-xs text-text-muted">
                    {action.shipment_id} · {_money(action.value_usd)} · risk {action.risk_score.toFixed(2)} · auto-executed
                  </span>
                </span>
              </li>
            ))}
            {incident.pending_approval.map((action) => (
              <li
                key={action.id}
                className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/[0.06] px-3 py-2 text-sm"
              >
                <ShieldWarning size={16} weight="fill" className="mt-0.5 shrink-0 text-amber-400" />
                <span className="min-w-0">
                  <span className="block font-medium text-amber-200">{action.action}</span>
                  <span className="text-xs text-text-muted">
                    {action.shipment_id} · {_money(action.value_usd)} · risk {action.risk_score.toFixed(2)} · awaiting approval
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {priorityOrder.length > 0 && (
        <div className="relative mt-5 rounded-xl border border-accent/20 bg-accent-soft p-3">
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-accent">
            <Lightning size={14} weight="fill" />
            Priority order
          </p>
          <ol className="mt-2 space-y-1 text-sm">
            {priorityOrder.map((item, index) => (
              <li key={item} className="flex items-center gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[11px] font-semibold text-accent">
                  {index + 1}
                </span>
                <span className="truncate">{item}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </aside>
  );
}

function _money(value: number): string {
  return `$${Math.round(value).toLocaleString()}`;
}

function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone: "danger" | "warning" | "recovering";
}) {
  const toneClass = {
    danger: "border-red-500/25 bg-red-500/[0.07] text-red-200",
    warning: "border-amber-500/25 bg-amber-500/[0.07] text-amber-200",
    recovering: "border-accent/25 bg-accent-soft text-accent",
  }[tone];

  return (
    <div className={`rounded-xl border p-3 ${toneClass}`}>
      <p className="text-[10px] font-medium uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-text">{value}</p>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: "watch" | "elevated" | "critical" }) {
  const toneClass = {
    watch: "bg-accent/20 text-accent",
    elevated: "bg-amber-500/20 text-amber-300",
    critical: "bg-red-500/20 text-red-300",
  }[severity];

  return (
    <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${toneClass}`}>
      {severity}
    </span>
  );
}

function ChainNode({
  icon,
  title,
  detail,
  status,
  tone,
  pulse,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  status: string;
  tone: "danger" | "warning" | "recovering";
  pulse?: boolean;
}) {
  const toneClass = {
    danger: "border-red-500/30 bg-red-500/[0.08] text-red-200",
    warning: "border-amber-500/30 bg-amber-500/[0.08] text-amber-200",
    recovering: "border-accent/30 bg-accent-soft text-accent",
  }[tone];

  const glowClass = {
    danger: "shadow-[0_0_24px_rgba(248,113,113,0.18)]",
    warning: "shadow-[0_0_24px_rgba(251,191,36,0.16)]",
    recovering: "shadow-[0_0_24px_rgba(91,141,239,0.16)]",
  }[tone];

  return (
    <motion.div
      className={`relative rounded-xl border p-3 ${toneClass} ${glowClass}`}
      whileHover={{ scale: 1.01 }}
    >
      {pulse && (
        <span className="absolute -right-1 -top-1 flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-60" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-red-400" />
        </span>
      )}
      <div className="flex items-start gap-3">
        <span className="mt-0.5">{icon}</span>
        <div className="min-w-0">
          <p className="font-medium text-text">{title}</p>
          <p className="mt-1 text-sm">{detail}</p>
          <p className="mt-1 truncate text-xs text-text-muted">{status}</p>
        </div>
      </div>
    </motion.div>
  );
}

function Connector({ damaged }: { damaged: boolean }) {
  return (
    <div className="flex items-center gap-3 px-4 text-xs text-text-muted">
      <span className={`h-8 w-px ${damaged ? "bg-red-400/60" : "bg-border"}`} />
      <ArrowRight size={14} weight="bold" className={damaged ? "text-red-300" : ""} />
      <span>{damaged ? "damage propagating" : "controlled handoff"}</span>
    </div>
  );
}

function OpenUILangBlock({ source }: { source: string }) {
  return (
    <details className="mt-3 rounded-lg border border-border bg-bg/50 p-2">
      <summary className="cursor-pointer text-xs font-medium text-accent">
        OpenUI Lang output
      </summary>
      <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-5 text-text-muted">
        {source}
      </pre>
    </details>
  );
}
