"use client";

import { motion } from "motion/react";
import { Gauge, ListChecks, ShieldCheck, Globe } from "@phosphor-icons/react/dist/ssr";
import { Incident } from "@/lib/api";

export function StatCards({ incident }: { incident: Incident | null }) {
  const totalActions = incident ? incident.auto_executed.length + incident.pending_approval.length : 0;
  const autoRate =
    totalActions > 0 ? Math.round((incident!.auto_executed.length / totalActions) * 100) : null;

  const stats = [
    {
      label: "Supplier regions monitored",
      value: "14",
      icon: Globe,
    },
    {
      label: "Current severity",
      value: incident ? incident.weather.risk_level : "—",
      icon: Gauge,
      highlight: incident?.weather.risk_level === "severe",
    },
    {
      label: "Shipments at risk",
      value: incident ? String(incident.impact.at_risk_shipments) : "—",
      icon: ListChecks,
    },
    {
      label: "Auto-execute rate",
      value: autoRate !== null ? `${autoRate}%` : "—",
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className={`rounded-2xl border p-4 ${
              stat.highlight ? "border-red-500/40 bg-red-500/[0.06]" : "border-border bg-surface"
            }`}
          >
            <div className="flex items-center justify-between text-text-muted">
              <span className="text-xs uppercase tracking-wide">{stat.label}</span>
              <Icon size={16} weight="bold" className={stat.highlight ? "text-red-300" : "text-accent"} />
            </div>
            <p className={`mt-2 text-2xl font-semibold capitalize ${stat.highlight ? "text-red-300" : ""}`}>
              {stat.value}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}
