import { Eye, ShieldCheck, ClockCounterClockwise, ChatCircleDots } from "@phosphor-icons/react/dist/ssr";
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
                  Polls weather data for every supplier region around the clock, no manual refresh.
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
                <h3 className="text-lg font-semibold">Supplier-aware reasoning</h3>
                <p className="mt-2 max-w-[34ch] text-sm leading-relaxed text-text-muted">
                  Knows which shipments, ports, and factories sit inside the forecast radius.
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
                <h3 className="text-lg font-semibold">Full audit trail</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  Every read, conclusion, and message is logged and timestamped.
                </p>
              </div>
            </div>
          </RevealItem>

          <RevealItem delay={0.2} className="md:col-span-2">
            <div className="relative flex h-full flex-col justify-between gap-6 overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-accent-soft to-surface p-6 md:min-h-[12rem]">
              <ChatCircleDots size={28} weight="bold" className="text-accent" />
              <div>
                <h3 className="text-lg font-semibold">Slack-native delivery</h3>
                <p className="mt-2 max-w-[40ch] text-sm leading-relaxed text-text-muted">
                  Alerts land where your team already works, formatted and ready to act on.
                </p>
              </div>
            </div>
          </RevealItem>
        </div>
      </div>
    </section>
  );
}
