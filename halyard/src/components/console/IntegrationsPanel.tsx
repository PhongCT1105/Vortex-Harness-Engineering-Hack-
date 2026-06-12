"use client";

import { motion } from "motion/react";
import {
  CloudLightning,
  Brain,
  Database,
  PaperPlaneTilt,
  ShieldCheck,
  Sparkle,
  Cloud,
  Plugs,
} from "@phosphor-icons/react/dist/ssr";
import { IntegrationStatus, setConfig } from "@/lib/api";

type Service = {
  key: string;
  label: string;
  description: string;
  icon: typeof CloudLightning;
  connected: (status: IntegrationStatus | null) => boolean | null;
};

const SERVICES: Service[] = [
  {
    key: "jua",
    label: "Jua",
    description: "Live weather forecasts feeding the Weather agent",
    icon: CloudLightning,
    connected: (s) => s?.jua ?? null,
  },
  {
    key: "reasoning",
    label: "Reasoning model",
    description: "Claude / DeepSeek power the agent reasoning steps",
    icon: Brain,
    connected: (s) => (s ? s.anthropic || s.deepseek : null),
  },
  {
    key: "composio",
    label: "Composio",
    description: "Sends approved actions to Slack & email",
    icon: PaperPlaneTilt,
    connected: (s) => s?.slack ?? null,
  },
  {
    key: "airbyte",
    label: "Airbyte",
    description: "Connector pulling procurement & shipment data",
    icon: Plugs,
    connected: (s) => s?.airbyte ?? null,
  },
  {
    key: "clickhouse",
    label: "ClickHouse",
    description: "Durable event log for the full audit trail",
    icon: Database,
    connected: (s) => s?.clickhouse ?? null,
  },
  {
    key: "guild",
    label: "Guild",
    description: "Governs triggers and the human-approval gate",
    icon: ShieldCheck,
    connected: () => true,
  },
  {
    key: "openui",
    label: "OpenUI",
    description: "Adaptive incident console, generated per severity",
    icon: Sparkle,
    connected: () => true,
  },
  {
    key: "render",
    label: "Render",
    description: "Hosts the backend API and this console",
    icon: Cloud,
    connected: () => true,
  },
];

const MODEL_OPTIONS: { value: "claude" | "deepseek"; label: string }[] = [
  { value: "claude", label: "Claude" },
  { value: "deepseek", label: "DeepSeek" },
];

export function IntegrationsPanel({
  status,
  setStatus,
}: {
  status: IntegrationStatus | null;
  setStatus: (s: IntegrationStatus) => void;
}) {
  async function handleSelectModel(model: "claude" | "deepseek") {
    const result = await setConfig({ ACTIVE_MODEL: model });
    setStatus(result);
  }

  return (
    <section className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Plugs size={20} weight="bold" className="text-accent" />
          Integrations
        </h2>
      </div>
      <p className="mb-5 text-sm text-text-muted">
        API keys are configured server-side and never exposed to this console.
      </p>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {SERVICES.map((service, i) => {
          const Icon = service.icon;
          const connected = service.connected(status);
          return (
            <motion.div
              key={service.key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="rounded-xl border border-border bg-surface-2 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-accent">
                  <Icon size={16} weight="bold" />
                </div>
                <span
                  className={`flex items-center gap-1.5 text-xs font-medium ${
                    connected === null
                      ? "text-text-muted"
                      : connected
                        ? "text-emerald-400"
                        : "text-text-muted"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      connected === null
                        ? "bg-text-muted/40"
                        : connected
                          ? "bg-emerald-400"
                          : "bg-text-muted/40"
                    }`}
                  />
                  {connected === null ? "n/a" : connected ? "live" : "mock"}
                </span>
              </div>
              <p className="mt-3 text-sm font-medium">{service.label}</p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">{service.description}</p>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-5 border-t border-border pt-5">
        <p className="mb-2 text-sm font-medium text-text-muted">Reasoning model</p>
        <div className="inline-flex rounded-full border border-border bg-surface-2 p-1">
          {MODEL_OPTIONS.map((opt) => {
            const active = (status?.active_model ?? "claude") === opt.value;
            const connected = opt.value === "claude" ? status?.anthropic : status?.deepseek;
            return (
              <button
                key={opt.value}
                onClick={() => handleSelectModel(opt.value)}
                className={`relative flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  active ? "bg-accent text-white" : "text-text-muted hover:text-text"
                }`}
              >
                {opt.label}
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-text-muted/40"}`} />
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-text-muted">
          Switches which model interprets scenarios. Falls back automatically if the selected key isn&apos;t configured.
        </p>
      </div>
    </section>
  );
}
