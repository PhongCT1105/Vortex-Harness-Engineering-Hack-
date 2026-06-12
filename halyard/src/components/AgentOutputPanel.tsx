"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  CloudLightning,
  Brain,
  PaperPlaneTilt,
  CheckCircle,
  Robot,
} from "@phosphor-icons/react/dist/ssr";
import { AgentEventRow } from "@/lib/api";

const KIND_META: Record<
  string,
  { label: string; icon: typeof Robot; summary: (payload: unknown) => string }
> = {
  weather_detected: {
    label: "Weather agent",
    icon: CloudLightning,
    summary: (p) => {
      const w = p as { affected_countries?: string[]; risk_level?: string; source?: string };
      return `Read live conditions for ${w.affected_countries?.join(", ") ?? "the region"}. Risk level: ${w.risk_level ?? "unknown"} (source: ${w.source ?? "mock"}).`;
    },
  },
  impact_assessed: {
    label: "Impact agent",
    icon: Brain,
    summary: (p) => {
      const i = p as { affected_suppliers?: number; at_risk_shipments?: number };
      return `Cross-referenced the forecast against the supplier map. ${i.affected_suppliers ?? 0} suppliers and ${i.at_risk_shipments ?? 0} shipments fall inside the exposure radius.`;
    },
  },
  actions_generated: {
    label: "Mitigation agent",
    icon: PaperPlaneTilt,
    summary: (p) => {
      const list = Array.isArray(p) ? p : [];
      return `Drafted ${list.length} mitigation action${list.length === 1 ? "" : "s"} ranked by risk and shipment value.`;
    },
  },
  approval_requested: {
    label: "Mitigation agent",
    icon: PaperPlaneTilt,
    summary: (p) => {
      const a = p as { action?: string };
      return `Flagged for human sign-off: "${a.action ?? "an action"}".`;
    },
  },
  action_executed: {
    label: "Comms agent",
    icon: CheckCircle,
    summary: (p) => {
      const a = p as { action?: string; channel?: string; sent?: boolean };
      return `${a.sent ? "Sent" : "Logged"} via ${a.channel ?? "mock channel"}: "${a.action ?? "an action"}".`;
    },
  },
  ai_orchestration_completed: {
    label: "AI orchestration agent",
    icon: Robot,
    summary: (p) => {
      const o = p as { executive_summary?: string; source?: string; confidence?: number };
      const confidence = typeof o.confidence === "number" ? ` Confidence: ${o.confidence.toFixed(2)}.` : "";
      return `${o.executive_summary ?? "Completed incident orchestration."} Source: ${o.source ?? "AI"}.${confidence}`;
    },
  },
};

const MODEL_LABEL: Record<"claude" | "deepseek", string> = {
  claude: "Claude",
  deepseek: "DeepSeek",
};

export function AgentOutputPanel({
  logs,
  model,
  loading,
}: {
  logs: AgentEventRow[];
  model: "claude" | "deepseek";
  loading: boolean;
}) {
  const reduce = useReducedMotion();
  const recent = logs.slice().reverse().slice(0, 8);

  return (
    <section className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Robot size={20} weight="bold" className="text-accent" />
          Agent reasoning
        </h2>
        <span className="relative flex items-center gap-2 overflow-hidden rounded-full border border-border bg-surface-2 px-3 py-1 text-xs font-medium text-text-muted">
          {!reduce && (
            <motion.span
              className="pointer-events-none absolute inset-0 opacity-40"
              style={{
                background:
                  "conic-gradient(from 0deg, transparent, var(--color-accent), transparent 60%)",
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            />
          )}
          <span className="relative z-10 h-1.5 w-1.5 rounded-full bg-accent" />
          <span className="relative z-10">{MODEL_LABEL[model]}</span>
        </span>
      </div>

      {recent.length === 0 && !loading && (
        <p className="text-sm text-text-muted">
          No agent activity yet. Run a scenario to see step-by-step reasoning here.
        </p>
      )}

      <ul className="flex flex-col gap-3">
        <AnimatePresence initial={false}>
          {recent.map((log, i) => {
            const meta = KIND_META[log.kind];
            const Icon = meta?.icon ?? Robot;
            const text = meta?.summary(log.payload) ?? log.kind;
            return (
              <motion.li
                key={`${log.ts}-${log.kind}-${i}`}
                initial={reduce ? false : { opacity: 0, y: 8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.35, delay: i * 0.04, ease: [0.16, 1, 0.3, 1] }}
                className="flex items-start gap-3"
              >
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
                  <Icon size={16} weight="bold" />
                </div>
                <div className="flex-1 rounded-2xl rounded-tl-sm border border-border bg-surface-2 px-4 py-2.5">
                  <div className="mb-0.5 flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-text-muted">
                      {meta?.label ?? "Agent"}
                    </span>
                    <span className="font-mono text-xs text-text-muted">
                      {new Date(log.ts * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-text">{text}</p>
                </div>
              </motion.li>
            );
          })}
        </AnimatePresence>

        {loading && (
          <motion.li
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-start gap-3"
          >
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
              <Robot size={16} weight="bold" />
            </div>
            <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-border bg-surface-2 px-4 py-3">
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-accent"
                  animate={reduce ? {} : { y: [0, -4, 0], opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
                />
              ))}
            </div>
          </motion.li>
        )}
      </ul>
    </section>
  );
}
