import { agentEvents } from "@/lib/events";
import { RevealItem } from "./RevealItem";

const actorLabel: Record<string, string> = {
  monitor: "MONITOR",
  reason: "REASON",
  act: "ACT",
  human: "APPROVAL",
};

export function LiveAuditLog() {
  return (
    <section className="border-b border-border bg-surface">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] lg:items-center">
          <div className="flex flex-col gap-4">
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Every action, on the record.
            </h2>
            <p className="max-w-[40ch] text-base leading-relaxed text-text-muted">
              StormOps keeps a running log of what it saw, what it concluded, and what it sent, so nothing happens off the books.
            </p>
          </div>

          <RevealItem>
            <div className="overflow-hidden rounded-2xl border border-border bg-bg">
              <div className="flex items-center justify-between border-b border-border px-5 py-3">
                <span className="text-sm font-medium text-text-muted">Incident #4471, Gulf Coast storm cell</span>
                <span className="font-mono text-xs text-text-muted">2026-06-12</span>
              </div>
              <ul className="divide-y divide-border">
                {agentEvents.map((event) => (
                  <li key={event.time} className="flex items-center gap-4 px-5 py-3 font-mono text-sm">
                    <span className="w-20 shrink-0 text-text-muted">{event.time}</span>
                    <span className="w-24 shrink-0 text-xs text-accent">{actorLabel[event.actor]}</span>
                    <span className="text-text">{event.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          </RevealItem>
        </div>
      </div>
    </section>
  );
}
