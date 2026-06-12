import { Eye, ShieldCheck, ClockCounterClockwise, ChatCircleDots, SquaresFour } from "@phosphor-icons/react/dist/ssr";
import { Brain } from "@phosphor-icons/react/dist/ssr";
import { RevealItem } from "./RevealItem";

export function Capabilities() {
  return (
    <section id="capabilities" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-28">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
          What runs while you sleep.
        </h2>

        <div className="mt-14 grid gap-4 md:grid-cols-4">
          <RevealItem className="md:col-span-2">
            <div className="relative flex h-full flex-col justify-between gap-6 overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-accent-soft to-surface p-6 md:min-h-[14rem]">
              <Eye size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">Always-on monitoring</h3>
                <p className="mt-2 max-w-[34ch] text-sm leading-relaxed text-text-muted">
                  Polls live weather data for every supplier region every few hours, no manual refresh.
                </p>
              </div>
            </div>
          </RevealItem>

          <RevealItem delay={0.05} className="md:col-span-2">
            <div
              className="relative flex h-full flex-col justify-between gap-6 overflow-hidden rounded-2xl border border-border bg-surface p-6 md:min-h-[14rem]"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 1px 1px, var(--color-border) 1px, transparent 0)",
                backgroundSize: "16px 16px",
              }}
            >
              <Brain size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">Claude-powered reasoning</h3>
                <p className="mt-2 max-w-[34ch] text-sm leading-relaxed text-text-muted">
                  Anthropic Claude ranks exposure, explains the call, and proposes a recovery plan grounded in your shipment data.
                </p>
              </div>
            </div>
          </RevealItem>

          <RevealItem delay={0.1}>
            <div className="flex h-full flex-col justify-between gap-6 rounded-2xl border border-border bg-surface p-6 md:min-h-[12rem]">
              <ShieldCheck size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">Human approval gate</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  Nothing sends without a person signing off first.
                </p>
              </div>
            </div>
          </RevealItem>

          <RevealItem delay={0.15}>
            <div className="flex h-full flex-col justify-between gap-6 rounded-2xl border border-border bg-surface p-6 md:min-h-[12rem]">
              <ClockCounterClockwise size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">ClickHouse audit trail</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  Every detection, decision, and dispatch is written to ClickHouse and timestamped.
                </p>
              </div>
            </div>
          </RevealItem>

          <RevealItem delay={0.2}>
            <div className="flex h-full flex-col justify-between gap-6 rounded-2xl border border-border bg-surface p-6 md:min-h-[12rem]">
              <SquaresFour size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">OpenUI incident maps</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  Ask the incident a question and get a live OpenUI damage map back — severity, value at risk, and the recovery plan.
                </p>
              </div>
            </div>
          </RevealItem>

          <RevealItem delay={0.25} className="md:col-span-2">
            <div className="relative flex h-full flex-col justify-between gap-6 overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-accent-soft to-surface p-6 md:min-h-[12rem]">
              <ChatCircleDots size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">Slack-native delivery</h3>
                <p className="mt-2 max-w-[40ch] text-sm leading-relaxed text-text-muted">
                  Auto-executed actions and approval requests land in Slack, formatted and ready to act on.
                </p>
              </div>
            </div>
          </RevealItem>
        </div>
      </div>
    </section>
  );
}
