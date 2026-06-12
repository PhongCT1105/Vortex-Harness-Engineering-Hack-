import { CloudLightning } from "@phosphor-icons/react/dist/ssr";

export function Footer() {
  return (
    <footer className="mt-auto">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-4 px-6 py-10 text-sm text-text-muted md:flex-row md:justify-between">
        <div className="flex items-center gap-2 font-medium text-text">
          <CloudLightning size={18} weight="duotone" className="text-accent" />
          StormOps
        </div>
        <p>Built for the Harness Engineering Hack, 2026.</p>
      </div>
    </footer>
  );
}
