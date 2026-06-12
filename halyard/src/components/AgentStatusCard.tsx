"use client";

import { motion, useReducedMotion } from "motion/react";
import { CloudLightning, Brain, PaperPlaneTilt, CheckCircle } from "@phosphor-icons/react/dist/ssr";
import { agentEvents } from "@/lib/events";

const icons = {
  monitor: CloudLightning,
  reason: Brain,
  act: PaperPlaneTilt,
  human: CheckCircle,
};

export function AgentStatusCard() {
  const reduce = useReducedMotion();
  const recent = agentEvents.slice(0, 4);

  return (
    <div className="w-full rounded-2xl border border-border bg-surface p-5 shadow-[0_24px_80px_-32px_rgba(91,141,239,0.35)]">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <motion.span
              className="absolute inset-0 rounded-full bg-accent"
              animate={reduce ? {} : { opacity: [0.6, 0.15, 0.6], scale: [1, 1.8, 1] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
            />
            <span className="absolute inset-0 rounded-full bg-accent" />
          </span>
          <span className="text-sm font-medium">Monitoring 14 supplier regions</span>
        </div>
        <span className="font-mono text-xs text-text-muted">live</span>
      </div>

      <ul className="mt-4 flex flex-col gap-3">
        {recent.map((event, i) => {
          const Icon = icons[event.actor];
          return (
            <motion.li
              key={event.time}
              initial={reduce ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: i * 0.12, ease: [0.16, 1, 0.3, 1] }}
              className="flex items-start gap-3"
            >
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
                <Icon size={14} weight="bold" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm text-text">{event.text}</span>
                <span className="font-mono text-xs text-text-muted">{event.time}</span>
              </div>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
