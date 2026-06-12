const integrations = [
  { slug: "anthropic", name: "Anthropic" },
  { slug: "render", name: "Render" },
  { slug: "clickhouse", name: "ClickHouse" },
  { slug: "airbyte", name: "Airbyte" },
  { slug: "zapier", name: "Zapier" },
];

export function IntegrationStrip() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <p className="mb-6 text-center text-sm text-text-muted">Built on</p>
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6">
          {integrations.map((item) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={item.slug}
              src={`https://cdn.simpleicons.org/${item.slug}/9aa1ad`}
              alt={item.name}
              className="h-6 w-auto opacity-70 transition-opacity hover:opacity-100"
            />
          ))}
        </div>
      </div>
    </section>
  );
}
