import { RevealItem } from "./RevealItem";

export function Quote() {
  return (
    <section className="border-b border-border bg-surface">
      <div className="mx-auto max-w-4xl px-6 py-20 text-center lg:py-28">
        <RevealItem>
          <p className="text-2xl font-medium leading-relaxed tracking-tight md:text-3xl">
            &ldquo;We used to find out about a port closure from the news. Now we get a Slack
            message with the supplier list already attached.&rdquo;
          </p>
          <div className="mt-6 flex flex-col items-center gap-0.5">
            <span className="text-sm font-medium">Daniela Ferreira</span>
            <span className="text-sm text-text-muted">Head of Operations, Norrbridge Supply Co.</span>
          </div>
        </RevealItem>
      </div>
    </section>
  );
}
