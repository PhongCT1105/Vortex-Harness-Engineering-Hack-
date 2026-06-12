const integrations = [
  { slug: "anthropic", name: "Anthropic", kind: "simpleicon" as const },
  { slug: "clickhouse", name: "ClickHouse", kind: "simpleicon" as const },
  { slug: "airbyte", name: "Airbyte", kind: "simpleicon" as const },
  { name: "Slack", kind: "slack" as const },
  { slug: "render", name: "Render", kind: "simpleicon" as const },
  { name: "OpenUI", kind: "openui" as const },
];

export function IntegrationStrip() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <p className="mb-6 text-center text-sm text-text-muted">Built on</p>
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6">
          {integrations.map((item) => {
            if (item.kind === "simpleicon") {
              return (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={item.slug}
                  src={`https://cdn.simpleicons.org/${item.slug}/9aa1ad`}
                  alt={item.name}
                  className="h-6 w-auto opacity-70 transition-opacity hover:opacity-100"
                />
              );
            }
            if (item.kind === "slack") {
              return (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key="slack"
                  src="https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/slack.svg"
                  alt="Slack"
                  className="h-6 w-auto opacity-60 grayscale transition-all hover:opacity-100 hover:grayscale-0"
                />
              );
            }
            return (
              <span
                key="openui"
                className="flex h-6 items-center rounded-md border border-text-muted/30 px-2 text-xs font-semibold tracking-wide text-text-muted opacity-70 transition-opacity hover:opacity-100"
              >
                OpenUI
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}
