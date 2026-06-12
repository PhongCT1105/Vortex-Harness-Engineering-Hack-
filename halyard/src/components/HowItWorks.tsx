import { CloudLightning, GitBranch, Brain, PaperPlaneTilt } from "@phosphor-icons/react/dist/ssr";
import { RevealItem } from "./RevealItem";

const steps = [
  {
    icon: CloudLightning,
    title: "Monitor",
    body: "Polls live weather data (Jua / Open-Meteo) for every region your suppliers operate in, continuously.",
  },
  {
    icon: GitBranch,
    title: "Map impact",
    body: "Cross-references the forecast against your supply chain map to find exposed shipments, suppliers, and dollar value at risk.",
  },
  {
    icon: Brain,
    title: "Reason",
    body: "Claude ranks the damage, drafts mitigations, and decides what's safe to auto-execute vs. what needs sign-off.",
  },
  {
    icon: PaperPlaneTilt,
    title: "Act & log",
    body: "Auto-runs low-risk fixes, sends approval requests to Slack, and writes every step to ClickHouse for audit.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-28">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
          One pipeline, four moves.
        </h2>

        <div className="relative mt-14 grid gap-10 md:grid-cols-4 md:gap-6">
          <div
            aria-hidden
            className="absolute top-6 left-0 hidden h-px w-full bg-border md:block"
          />
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <RevealItem key={step.title} delay={i * 0.1}>
                <div className="relative flex flex-col gap-4">
                  <div className="relative z-10 flex h-12 w-12 items-center justify-center rounded-full bg-bg ring-1 ring-border">
                    <Icon size={22} weight="bold" className="text-accent" />
                  </div>
                  <h3 className="text-xl font-semibold">{step.title}</h3>
                  <p className="max-w-[32ch] text-sm leading-relaxed text-text-muted">
                    {step.body}
                  </p>
                </div>
              </RevealItem>
            );
          })}
        </div>
      </div>
    </section>
  );
}
