"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import {
  CloudLightning,
  SquaresFour,
  Cube,
  Robot,
  ChatCircleText,
  ShieldWarning,
  ListBullets,
  Plugs,
  ArrowSquareOut,
} from "@phosphor-icons/react/dist/ssr";

export const TABS = [
  { key: "overview", label: "Overview", icon: SquaresFour },
  { key: "pipeline", label: "Pipeline", icon: Cube },
  { key: "reasoning", label: "Agent reasoning", icon: Robot },
  { key: "ask", label: "Ask incident", icon: ChatCircleText },
  { key: "actions", label: "Actions & approvals", icon: ShieldWarning },
  { key: "audit", label: "Audit log", icon: ListBullets },
  { key: "integrations", label: "Integrations", icon: Plugs },
] as const;

export type TabKey = (typeof TABS)[number]["key"];

export function ConsoleShell({
  active,
  onChange,
  statusSlot,
  children,
}: {
  active: TabKey;
  onChange: (tab: TabKey) => void;
  statusSlot?: React.ReactNode;
  children: React.ReactNode;
}) {
  const activeTab = TABS.find((t) => t.key === active);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg lg:grid lg:grid-cols-[15rem_1fr]">
      {/* Sidebar */}
      <aside className="hidden h-screen min-w-0 flex-col border-r border-border bg-surface/60 px-4 py-6 lg:flex">
        <Link href="/" className="mb-8 flex items-center gap-2 px-2 font-semibold tracking-tight">
          <CloudLightning size={20} weight="duotone" className="text-accent" />
          StormOps
        </Link>

        <nav className="flex flex-1 flex-col gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = active === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => onChange(tab.key)}
                className={`flex items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-text-muted hover:bg-surface-2 hover:text-text"
                }`}
              >
                <Icon size={18} weight="bold" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        <Link
          href="/"
          className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-text-muted transition-colors hover:bg-surface-2 hover:text-text"
        >
          <ArrowSquareOut size={16} weight="bold" />
          Back to marketing site
        </Link>
      </aside>

      {/* Main */}
      <div className="flex h-screen min-w-0 flex-col overflow-hidden">
        <header className="flex shrink-0 items-center justify-between border-b border-border bg-bg/80 px-6 py-4 backdrop-blur-md lg:px-10">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-accent">
              <CloudLightning size={14} weight="bold" />
              StormOps Console
            </div>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">
              {activeTab?.label ?? "Mission control"}
            </h1>
          </div>
          {statusSlot}
        </header>

        {/* Mobile tab bar */}
        <nav className="flex shrink-0 gap-1 overflow-x-auto border-b border-border bg-surface/40 px-4 py-2 lg:hidden">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = active === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => onChange(tab.key)}
                className={`flex shrink-0 items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive ? "bg-accent text-white" : "bg-surface-2 text-text-muted"
                }`}
              >
                <Icon size={14} weight="bold" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-8 lg:px-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={active}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col gap-6"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
