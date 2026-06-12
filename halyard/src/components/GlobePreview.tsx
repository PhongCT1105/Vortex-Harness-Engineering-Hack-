"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Globe as GlobeIcon } from "@phosphor-icons/react/dist/ssr";
import { RevealItem } from "./RevealItem";
import { SupplyChainGlobe } from "./supply-chain/SupplyChainGlobe";
import { SupplyChain, getSupplyChain } from "@/lib/api";

export function GlobePreview() {
  const [data, setData] = useState<SupplyChain | null>(null);

  useEffect(() => {
    getSupplyChain()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  return (
    <section className="border-b border-border bg-surface">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] lg:items-center lg:py-28">
        <RevealItem>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-accent">
            <GlobeIcon size={14} weight="bold" />
            Live supply chain map
          </div>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            See every supplier, in one place.
          </h2>
          <p className="mt-4 max-w-[40ch] text-base leading-relaxed text-text-muted">
            Upload a CSV of your suppliers and StormOps plots every shipment — country,
            component, value, criticality — onto a live globe routed to your assembly
            plant. When a storm hits one of these regions, the agent already knows
            exactly what&apos;s exposed.
          </p>
          <a
            href="/supply-chain"
            className="mt-6 inline-flex items-center gap-2 rounded-full border border-border px-5 py-3 text-sm font-medium text-text transition-colors hover:border-accent hover:text-accent"
          >
            Map your supply chain
            <ArrowRight size={16} weight="bold" />
          </a>
        </RevealItem>

        <RevealItem delay={0.1}>
          <div className="relative h-[22rem] overflow-hidden rounded-2xl border border-border bg-bg sm:h-[28rem]">
            {data ? (
              <SupplyChainGlobe data={data} />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-muted">
                Loading live supply chain…
              </div>
            )}
          </div>
        </RevealItem>
      </div>
    </section>
  );
}
