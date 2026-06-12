"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { SupplyChain, SupplyChainNode } from "@/lib/api";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

const ACCENT = "#5b8def";
const ACCENT_GLOW = "#8fb3ff";
const ASSEMBLY_COLOR = "#f4a23a";

type ArcDatum = {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  color: string[];
  supplier: SupplyChainNode;
};

type PointDatum = {
  lat: number;
  lng: number;
  size: number;
  color: string;
  label: string;
  kind: "supplier" | "assembly";
  node?: SupplyChainNode;
};

export function SupplyChainGlobe({
  data,
  onSelectNode,
}: {
  data: SupplyChain;
  onSelectNode?: (node: SupplyChainNode | null) => void;
}) {
  const globeRef = useRef<{
    pointOfView: (pov: { lat: number; lng: number; altitude: number }, ms?: number) => void;
    controls: () => { autoRotate: boolean; autoRotateSpeed: number };
  } | null>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDims({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    g.pointOfView({ lat: data.assembly.lat, lng: data.assembly.lng, altitude: 1.8 }, 1200);
    const controls = g.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
  }, [data]);

  const arcsData: ArcDatum[] = useMemo(
    () =>
      data.arcs.map((arc) => ({
        startLat: arc.startLat,
        startLng: arc.startLng,
        endLat: arc.endLat,
        endLng: arc.endLng,
        color: [ACCENT_GLOW, ASSEMBLY_COLOR],
        supplier: data.nodes.find((n) => n.id === arc.supplier_id) as SupplyChainNode,
      })),
    [data]
  );

  const pointsData: PointDatum[] = useMemo(() => {
    const supplierPoints: PointDatum[] = data.nodes.map((node) => ({
      lat: node.lat,
      lng: node.lng,
      size: 0.55 + node.criticality * 0.6,
      color: ACCENT_GLOW,
      label: `${node.component} — ${node.country}`,
      kind: "supplier",
      node,
    }));
    const assemblyPoint: PointDatum = {
      lat: data.assembly.lat,
      lng: data.assembly.lng,
      size: 1.4,
      color: ASSEMBLY_COLOR,
      label: `${data.assembly.name} — ${data.assembly.city}, ${data.assembly.country}`,
      kind: "assembly",
    };
    return [...supplierPoints, assemblyPoint];
  }, [data]);

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <Globe
        ref={globeRef as never}
        width={dims.width}
        height={dims.height}
        backgroundColor="rgba(0,0,0,0)"
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        atmosphereColor={ACCENT}
        atmosphereAltitude={0.22}
        arcsData={arcsData}
        arcColor="color"
        arcDashLength={0.4}
        arcDashGap={0.25}
        arcDashAnimateTime={2600}
        arcStroke={0.5}
        arcAltitudeAutoScale={0.32}
        pointsData={pointsData}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude={0.01}
        pointRadius={(d: object) => (d as PointDatum).size * 0.45}
        pointLabel={(d: object) => (d as PointDatum).label}
        onPointClick={(point: object) => {
          const p = point as PointDatum;
          onSelectNode?.(p.node ?? null);
        }}
        labelsData={pointsData}
        labelLat="lat"
        labelLng="lng"
        labelText={(d: object) => (d as PointDatum).label}
        labelSize={(d: object) => ((d as PointDatum).kind === "assembly" ? 0.85 : 0.55)}
        labelColor={(d: object) => ((d as PointDatum).kind === "assembly" ? ASSEMBLY_COLOR : "rgba(255,255,255,0.75)")}
        labelDotRadius={0}
        labelAltitude={0.012}
        labelResolution={2}
      />
    </div>
  );
}
