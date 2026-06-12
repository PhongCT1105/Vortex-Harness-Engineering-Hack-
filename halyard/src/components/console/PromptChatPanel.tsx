"use client";

import { FormEvent, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { motion } from "motion/react";
import {
  ArrowRight,
  ChatCircleText,
  Factory,
  GitBranch,
  PaperPlaneTilt,
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

  const suggested = lastResponse?.suggested_questions ?? DEFAULT_QUESTIONS;

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

  return (
    <aside className="rounded-2xl border border-border bg-surface p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-accent">
        OpenUI incident visualization
      </p>
      <h2 className="mt-1 text-lg font-semibold">Supply-chain damage map</h2>

      <div className="mt-5 space-y-3">
        <ChainNode
          icon={<WarningDiamond size={18} weight="bold" />}
          title="Weather zone"
          detail={incident.weather.affected_countries.join(", ")}
          status={`${incident.weather.risk_level} · ${incident.weather.wind_kmh} km/h wind`}
          tone="danger"
        />
        <Connector damaged />
        <ChainNode
          icon={<GitBranch size={18} weight="bold" />}
          title="Supplier lane"
          detail={`${incident.impact.at_risk_shipments} shipments exposed`}
          status={topShipments.map((s) => s.component).join(", ") || "No damaged lane"}
          tone="warning"
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

      <div className="mt-5 rounded-xl border border-border bg-bg/45 p-3">
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
              className="flex items-center justify-between gap-3 rounded-lg bg-surface-2 px-3 py-2 text-sm"
            >
              <span className="min-w-0">
                <span className="block truncate font-medium">{shipment.component}</span>
                <span className="text-xs text-text-muted">
                  {shipment.country} · {shipment.shipment_id}
                </span>
              </span>
              <span className="shrink-0 rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-300">
                {shipment.risk_score.toFixed(2)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

function ChainNode({
  icon,
  title,
  detail,
  status,
  tone,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
  status: string;
  tone: "danger" | "warning" | "recovering";
}) {
  const toneClass = {
    danger: "border-red-500/30 bg-red-500/[0.08] text-red-200",
    warning: "border-amber-500/30 bg-amber-500/[0.08] text-amber-200",
    recovering: "border-accent/30 bg-accent-soft text-accent",
  }[tone];

  return (
    <div className={`rounded-xl border p-3 ${toneClass}`}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5">{icon}</span>
        <div className="min-w-0">
          <p className="font-medium text-text">{title}</p>
          <p className="mt-1 text-sm">{detail}</p>
          <p className="mt-1 truncate text-xs text-text-muted">{status}</p>
        </div>
      </div>
    </div>
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
