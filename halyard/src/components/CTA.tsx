import { ArrowRight } from "@phosphor-icons/react/dist/ssr";

export function CTA() {
  return (
    <section id="cta" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:py-28">
        <div className="flex flex-col items-center gap-6 rounded-2xl border border-border bg-gradient-to-br from-accent-soft to-surface px-6 py-16 text-center">
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight md:text-4xl">
            Let the agent watch the forecast for you.
          </h2>
          <p className="max-w-[44ch] text-base leading-relaxed text-text-muted">
            Get StormOps running on your supplier map in an afternoon, with full approval controls from day one.
          </p>
          <a
            href="#"
            className="flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-transform active:scale-[0.98] hover:bg-accent/90"
          >
            Get access
            <ArrowRight size={16} weight="bold" />
          </a>
        </div>
      </div>
    </section>
  );
}
