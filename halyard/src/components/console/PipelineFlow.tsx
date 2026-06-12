"use client";

import { motion, useReducedMotion } from "motion/react";
import {
  CloudLightning,
  Brain,
  Compass,
  PaperPlaneTilt,
  Database,
  ShieldCheck,
  Cube,
  CheckCircle,
  CircleDashed,
  Lightning,
} from "@phosphor-icons/react/dist/ssr";
import { Incident } from "@/lib/api";

type NodeState = "idle" | "active" | "done" | "warn";

type FlowNode = {
  key: string;
  label: string;
  sublabel: string;
  helpText: string;
  icon: typeof CloudLightning;
};

const NODES: FlowNode[] = [
  {
    key: "trigger",
    label: "Trigger",
    sublabel: "NL event",
    helpText: "A natural-language event kicks off a new incident run.",
    icon: Lightning,
  },
  {
    key: "weather",
    label: "Weather agent",
    sublabel: "Jua forecast",
    helpText: "Pulls live forecast data and scores storm severity.",
    icon: CloudLightning,
  },
  {
    key: "impact",
    label: "Impact agent",
    sublabel: "Supplier graph",
    helpText: "Maps the weather risk onto suppliers and shipments.",
    icon: Compass,
  },
  {
    key: "mitigation",
    label: "Mitigation agent",
    sublabel: "Reroute / expedite",
    helpText: "Proposes reroutes, expedites, and approval-gated actions.",
    icon: Brain,
  },
  {
    key: "comms",
    label: "Comms agent",
    sublabel: "Slack · Email",
    helpText: "Sends alerts to Slack/email and logs the audit trail.",
    icon: PaperPlaneTilt,
  },
];

const STATE_STYLES: Record<NodeState, string> = {
  idle: "border-border bg-surface-2 text-text-muted",
  active: "border-accent bg-accent-soft text-accent",
  done: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  warn: "border-amber-500/40 bg-amber-500/10 text-amber-300",
};

export function PipelineFlow({
  incident,
  loading,
}: {
  incident: Incident | null;
  loading: boolean;
}) {
  const reduce = useReducedMotion();

  const states: NodeState[] = NODES.map((node, i) => {
    if (!incident && !loading) return "idle";
    if (loading) {
      // Pulse through nodes left-to-right while running.
      return i === 0 || (incident && i <= 4) ? "active" : "idle";
    }
    if (!incident) return "idle";
    if (node.key === "comms") {
      if (incident.pending_approval.length > 0 && incident.auto_executed.length === 0) {
        return "warn";
      }
      return "done";
    }
    return "done";
  });

  const hasPending = !!incident && incident.pending_approval.length > 0;

  return (
    <section className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Cube size={20} weight="bold" className="text-accent" />
          Agent pipeline
        </h2>
        <span className="text-xs text-text-muted">
          {loading ? "Running…" : incident ? `Incident ${incident.incident_id}` : "Idle"}
        </span>
      </div>

      {/* Stepper */}
      <div className="flex items-stretch gap-2 overflow-x-auto pb-2">
        {NODES.map((node, i) => {
          const state = states[i];
          const Icon = node.icon;
          return (
            <div key={node.key} className="flex items-center">
              <motion.div
                initial={false}
                animate={
                  state === "active" && !reduce
                    ? { scale: [1, 1.03, 1] }
                    : { scale: 1 }
                }
                transition={{ duration: 1.4, repeat: state === "active" ? Infinity : 0, ease: "easeInOut" }}
                className={`flex min-w-[11.5rem] flex-col gap-2 rounded-xl border px-3.5 py-3 transition-colors ${STATE_STYLES[state]}`}
              >
                <div className="flex items-center justify-between">
                  <Icon size={18} weight="bold" />
                  {state === "done" && <CheckCircle size={14} weight="bold" />}
                  {state === "warn" && <ShieldCheck size={14} weight="bold" />}
                  {state === "idle" && <CircleDashed size={14} weight="bold" className="opacity-50" />}
                </div>
                <div>
                  <p className="text-sm font-medium leading-tight">{node.label}</p>
                  <p className="mt-0.5 text-[11px] leading-tight text-text-muted">{node.sublabel}</p>
                  <p className="mt-0.5 text-[10px] leading-tight text-text-muted/70">{node.helpText}</p>
                </div>
              </motion.div>
              {i < NODES.length - 1 && (
                <div className="flex w-6 shrink-0 items-center justify-center sm:w-8">
                  <div className={`h-px w-full ${state === "idle" ? "bg-border" : "bg-accent/40"}`} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Governance + logging sidecars */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div
          className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${
            hasPending
              ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
              : "border-border bg-surface-2 text-text-muted"
          }`}
        >
          <ShieldCheck size={18} weight="bold" />
          <div>
            <p className="font-medium text-text">Guild · tiered autonomy</p>
            <p className="text-xs">
              {hasPending
                ? `${incident?.pending_approval.length} action(s) gated for human approval`
                : "Low-risk actions auto-execute; high-value gated to a human"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-border bg-surface-2 px-4 py-3 text-sm text-text-muted">
          <Database size={18} weight="bold" />
          <div>
            <p className="font-medium text-text">ClickHouse · event log</p>
            <p className="text-xs">Every step persisted to <code className="font-mono">agent_events</code></p>
          </div>
        </div>
      </div>
    </section>
  );
}
