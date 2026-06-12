"use client";

import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import { AgentStatusCard } from "./AgentStatusCard";

export function Hero() {
  const reduce = useReducedMotion();
  const rise = {
    initial: reduce ? false : { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
  };

  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="mx-auto grid max-w-7xl items-center gap-12 px-6 pt-16 pb-20 lg:grid-cols-2 lg:pt-24 lg:pb-28">
        <div className="flex flex-col gap-6">
          <motion.h1
            {...rise}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl lg:text-6xl"
          >
            Weather risk, caught before it&apos;s a problem.
          </motion.h1>
          <motion.p
            {...rise}
            transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-[42ch] text-lg leading-relaxed text-text-muted"
          >
            StormOps watches live weather data, reasons about supplier exposure, and drafts the alert before anyone asks.
          </motion.p>
          <motion.div
            {...rise}
            transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap items-center gap-4"
          >
            <a
              href="/console"
              className="flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-medium text-white transition-transform active:scale-[0.98] hover:bg-accent/90"
            >
              Open console
              <ArrowRight size={16} weight="bold" />
            </a>
            <a
              href="#how-it-works"
              className="rounded-full border border-border px-5 py-3 text-sm font-medium text-text transition-colors hover:border-text-muted"
            >
              See how it works
            </a>
          </motion.div>
        </div>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="lg:justify-self-end lg:w-[26rem]"
        >
          <AgentStatusCard />
        </motion.div>
      </div>
    </section>
  );
}
