import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { IntegrationStrip } from "@/components/IntegrationStrip";
import { HowItWorks } from "@/components/HowItWorks";
import { GlobePreview } from "@/components/GlobePreview";
import { LiveAuditLog } from "@/components/LiveAuditLog";
import { Capabilities } from "@/components/Capabilities";
import { Quote } from "@/components/Quote";
import { CTA } from "@/components/CTA";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <>
      <Nav />
      <main className="flex flex-col">
        <Hero />
        <IntegrationStrip />
        <HowItWorks />
        <GlobePreview />
        <LiveAuditLog />
        <Capabilities />
        <Quote />
        <CTA />
      </main>
      <Footer />
    </>
  );
}
