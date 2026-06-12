import Link from "next/link";
import { CloudLightning } from "@phosphor-icons/react/dist/ssr";

const links = [
  { href: "#product", label: "Product" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="#" className="flex items-center gap-2 font-semibold tracking-tight">
          <CloudLightning size={20} weight="duotone" className="text-accent" />
          StormOps
        </Link>

        <nav className="hidden items-center gap-8 lg:flex">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-text-muted transition-colors hover:text-text"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <Link
          href="/console"
          className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-transform active:scale-[0.98] hover:bg-accent/90"
        >
          Open console
        </Link>
      </div>
    </header>
  );
}
