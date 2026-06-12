## Context

The current console (`halyard/src/app/console/page.tsx`) dispatches content via `tab` state managed in `ConsoleShell`. The shell renders a persistent sidebar with 8 nav items and a mobile tab bar; content is conditionally rendered per tab inside `<main>`. The 8 sections that must collapse into one page are: Supply Weather, Pipeline, Agent Reasoning, Ask Incident, Actions & Approvals, Audit Log, and Integrations (Overview is dissolved — its stat cards can move to the dashboard header row).

`react-globe.gl` is already installed. `motion/react` is the animation library throughout. All data fetching happens in `ConsolePage` and is passed down as props.

## Goals / Non-Goals

**Goals:**
- Replace tab routing with a single scrollable dashboard in `console/page.tsx`
- Hollow out `ConsoleShell` to only provide the fixed header (branding + status slot); remove sidebar and tab nav
- Apply all 8 UI changes within the new layout
- Zero new npm packages

**Non-Goals:**
- Changing any data-fetching logic or API calls
- Touching the marketing site, supply-chain page, or any file outside `halyard/src/app/console/` and `halyard/src/components/console/`
- Mobile optimization beyond what already exists
- Animating the layout transitions between sections

## Decisions

### ConsoleShell: hollow, keep header only

`ConsoleShell` today manages the sidebar, mobile tab bar, and `<main>` scroll container. Options:
1. Delete `ConsoleShell` entirely and inline the header.
2. Strip the sidebar/tab nav from `ConsoleShell` and keep it as a thin header wrapper.

Decision: **Option 2** — rename the props to remove `active`/`onChange`/tab concepts, keep the fixed header with branding and `statusSlot`, and let `<main>` become a passthrough. This avoids touching the header markup and keeps the `ModelBadge` integration intact. The `TABS` export and `TabKey` type are removed since no other file references them.

### Dashboard grid: CSS grid in `console/page.tsx`

The layout is defined directly in `ConsolePage`'s JSX, not in a new component. A `<div className="grid gap-6 lg:grid-cols-2">` wraps paired sections; full-width sections break out of the grid with `lg:col-span-2`. This is the simplest approach — no new layout component needed.

Layout structure:
```
<div class="flex flex-col gap-6">
  <StatCards />                          ← full width header row
  <div class="grid gap-6 lg:grid-cols-2">
    <SupplyWeatherSection />             ← left, row 1
    <PipelineFlow />                     ← right, row 1
    <AgentOutputPanel />                 ← left, row 2
    <ActionsSection />                   ← right, row 2
    <PromptChatPanel />                  ← left, row 3 (or lg:col-span-2 if Ask Incident needs full width)
  </div>
  <AuditLog />                           ← full width, collapsed by default
  <IntegrationsPanel />                  ← full width, bottom
</div>
```

Ask Incident (row 3) occupies the left column only; the right column in row 3 is empty at `lg` — the existing `SupplyChainSimulation` aside within `PromptChatPanel` fills the right half of the Ask Incident section internally (it already uses `xl:grid-cols-[1.1fr_0.9fr]`).

### Map library: `react-globe.gl` (existing)

`react-globe.gl` is installed and already used in `SupplyChainGlobe.tsx`. It supports arbitrary `pointsData` with lat/lng/color/altitude. Creating a thin `IncidentMap` wrapper avoids adding any dependency. The component MUST be dynamically imported with `next/dynamic({ ssr: false })` since it uses WebGL.

Country centroid lookup: a small static `CENTROIDS` record (≈40 countries, inline in `IncidentMap.tsx`) maps ISO country name strings from the API to lat/lng. The supply weather and weather agent responses both return country names.

### Gradient border: CSS wrapper div, no JS

Wrap the `<input>` in a `<div className="p-[1.5px] rounded-full bg-gradient-to-r from-blue-500 to-violet-600">` with a dark inner background. The input gets `border-0 bg-surface-2`. Focus state: add `group` to the wrapper, `group-focus-within:opacity-100` to boost gradient brightness — pure CSS, no JS.

### Actions reorder: markup inversion + `useState(false)` collapsible

The current `grid sm:grid-cols-2` is replaced with `flex flex-col gap-4`. Pending Approval block first in JSX. Auto-Executed wrapped in a collapsible using `useState(false)` and `AnimatePresence` — same pattern as `AuditLog`.

### ActionsChat: fixed bottom-right floating panel

Position: `fixed bottom-6 right-6 z-50`. Toggle: floating `ChatCircleText` button; `AnimatePresence` for open/close. Calls `askIncident(question, incident)` from `@/lib/api`. Not rendered when `incident` is null.

### Pipeline help text: third line in node card

Add `helpText: string` to `FlowNode`, render as `<p className="mt-0.5 text-[10px] leading-tight text-text-muted">` below `sublabel`.

### Integrations tile removal: delete two array entries

Remove `{ key: "jua" }` and `{ key: "composio" }` from `SERVICES` in `IntegrationsPanel.tsx`. Grid reflows automatically.

### Impact title: one-line string replacement

`console/page.tsx` line ~223: replace the interpolated string with the literal `"Impact"`.

## Risks / Trade-offs

- **`react-globe.gl` rendered twice on one page** (Supply Weather + Ask Incident): two WebGL contexts on the same page can be memory-intensive. Mitigation: set a fixed small height (`h-64`) and disable atmospheric glow/extras on the embedded instances. If perf issues arise, swap to a CSS-only SVG world map at 0 cost to the component interface.
- **Row 3 right column empty at `lg`**: Ask Incident already has an internal two-column layout (`xl:grid-cols-[1.1fr_0.9fr]`). When placed in the left column of the outer grid, this internal grid will likely be squished at `lg`. Mitigation: give Ask Incident `lg:col-span-2` so it spans full width, letting its internal grid breathe.
- **ConsoleShell tab state referenced nowhere after change**: the `tab` state and `setTab` in `ConsolePage` become dead code. Remove them in the same diff.
- **AuditLog already has its own collapsible**: the existing `AuditLog` component manages its own `open` state. No change needed — just render it directly.

## Migration Plan

1. Modify `ConsoleShell` to remove sidebar/tab nav (keep header shell).
2. Rewrite the `ConsolePage` JSX to the stacked grid layout.
3. Apply the 8 UI changes in their respective components/sections.
4. Build and verify (`npm run build` in `halyard/`).
5. Rollback: revert the commit; no state or DB migration needed.

## Open Questions

- Should `StatCards` remain at the top as a KPI header row, or be removed since it duplicates data already visible in the Supply Weather and Impact sections? (Suggestion: keep — it provides at-a-glance severity without scrolling.)
- Should Ask Incident span full width (`lg:col-span-2`) or occupy only the left column? (Suggestion: full width, because its internal split layout needs horizontal space.)
