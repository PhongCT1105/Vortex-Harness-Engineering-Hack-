"use client";

import Link from "next/link";
import { CloudLightning } from "@phosphor-icons/react/dist/ssr";

export function ConsoleShell({
  statusSlot,
  children,
}: {
  statusSlot?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between border-b border-border bg-bg/80 px-6 py-4 backdrop-blur-md lg:px-10">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-accent">
            <CloudLightning size={14} weight="bold" />
            StormOps Console
          </div>
        </Link>
        {statusSlot}
      </header>

      <main className="min-w-0 flex-1 px-6 py-8 lg:px-10">{children}</main>
    </div>
  );
}
