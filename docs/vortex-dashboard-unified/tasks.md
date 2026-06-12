## 1. Strip ConsoleShell to header-only

- [ ] 1.1 Remove `active`, `onChange` props and all tab-related logic from `ConsoleShell.tsx`
- [ ] 1.2 Delete the `TABS` const and `TabKey` type from `ConsoleShell.tsx`
- [ ] 1.3 Remove the sidebar `<aside>` block from `ConsoleShell.tsx`
- [ ] 1.4 Remove the mobile tab bar `<nav>` block from `ConsoleShell.tsx`
- [ ] 1.5 Keep the fixed `<header>` with branding and `statusSlot`; update `<main>` to be a simple scroll container passthrough

## 2. Restructure ConsolePage to single-page grid layout

- [ ] 2.1 Delete `tab`, `setTab` state and all `tab === "..."` conditional blocks from `console/page.tsx`
- [ ] 2.2 Remove the `ConsoleShell` `active`/`onChange` props from the call site in `console/page.tsx`
- [ ] 2.3 Add outer `<div className="flex flex-col gap-6">` wrapper for all dashboard content
- [ ] 2.4 Add `<StatCards incident={incident} />` as the full-width header row
- [ ] 2.5 Add `<div className="grid gap-6 lg:grid-cols-2">` grid container
- [ ] 2.6 Place Supply Weather section (left, row 1) inside the grid — extract the `SupplyWeatherPanel` render into the left column
- [ ] 2.7 Place `<PipelineFlow incident={incident} loading={loading} />` in the right column of row 1
- [ ] 2.8 Place `<AgentOutputPanel logs={logs} />` in the left column of row 2
- [ ] 2.9 Place the Actions & Approvals JSX block in the right column of row 2
- [ ] 2.10 Place `<PromptChatPanel incident={incident} logs={logs} />` with `lg:col-span-2` for row 3
- [ ] 2.11 Place `<AuditLog logs={logs} />` full-width below the grid
- [ ] 2.12 Place `<IntegrationsPanel status={status} setStatus={setStatus} />` full-width at the bottom
- [ ] 2.13 Remove the scenario trigger input/button from the old Overview tab — move it to the Supply Weather section header or above StatCards as a persistent run-scenario bar

## 3. Pipeline Node Help Text

- [ ] 3.1 Add `helpText: string` field to the `FlowNode` type in `PipelineFlow.tsx`
- [ ] 3.2 Populate `helpText` for all 5 entries in the `NODES` array with the specified one-sentence descriptions
- [ ] 3.3 Render `helpText` as `<p className="mt-0.5 text-[10px] leading-tight text-text-muted">` below `sublabel` in the node card

## 4. IncidentMap Component

- [ ] 4.1 Create `halyard/src/components/console/IncidentMap.tsx` with inner `GlobeMap` component wrapping `react-globe.gl`; props: `points: Array<{ lat: number; lng: number; label: string; severity?: "critical" | "elevated" | "watch" }>`
- [ ] 4.2 Implement severity → color mapping (red / amber / sky-blue / accent-blue)
- [ ] 4.3 Disable autorotation; set globe height to `h-64`; disable atmospheric extras for performance
- [ ] 4.4 Export default `IncidentMap` using `next/dynamic(() => import('./IncidentMap'), { ssr: false })` pattern (or wrap the globe-specific render inside a dynamic import at the top of the file)
- [ ] 4.5 Add a static `CENTROIDS` record mapping ~40 API-returned country name strings to lat/lng pairs

## 5. Supply Weather Section — Map Embed

- [ ] 5.1 Import `IncidentMap` in `console/page.tsx`
- [ ] 5.2 Render `IncidentMap` below the weather assessment content in the Supply Weather section, guarded by `incident !== null`
- [ ] 5.3 Derive map points from `incident.weather.affected_countries` (severity = `incident.weather.risk_level` mapped to critical/elevated/watch) and from `supplyWeather.countries` if loaded

## 6. Supply Weather — Simplify Impact Title

- [ ] 6.1 In `console/page.tsx`, find the Impact section `<h2>` and replace the interpolated title with the static string `"Impact"`

## 7. Ask Incident — Gradient Chat Input Border

- [ ] 7.1 In `PromptChatPanel.tsx`, wrap the `<input>` in `<div className="group p-[1.5px] flex-1 rounded-full bg-gradient-to-r from-blue-500 to-violet-600 transition-all focus-within:from-blue-400 focus-within:to-violet-500">`
- [ ] 7.2 Update the `<input>` className to remove `border border-border` and add `border-0 outline-none w-full`
- [ ] 7.3 Verify the form row (gradient wrapper + Ask button) remains on one line and aligned

## 8. Ask Incident — World Map Embed

- [ ] 8.1 Import `IncidentMap` in `PromptChatPanel.tsx`
- [ ] 8.2 Render `IncidentMap` below the message list `<div>` and above the suggested-question chips, guarded by `incident !== null`
- [ ] 8.3 Derive map points from `incident.weather.affected_countries` and `incident.impact.shipments` using the `CENTROIDS` lookup and risk_score thresholds

## 9. Actions Section — Reorder and Collapse Auto-Executed

- [ ] 9.1 In `console/page.tsx`, replace the Actions `grid sm:grid-cols-2` wrapper with `flex flex-col gap-4`
- [ ] 9.2 Move the Pending Approval `<div>` block to appear first in the JSX
- [ ] 9.3 Add `const [autoOpen, setAutoOpen] = useState(false)` state for the collapsible
- [ ] 9.4 Wrap the Auto-Executed content in a collapsible using `CaretDown` toggle and `AnimatePresence` (collapsed by default)

## 10. Actions Chatbot Agent

- [ ] 10.1 Create `halyard/src/components/console/ActionsChat.tsx` with props `{ incident: Incident | null }`
- [ ] 10.2 Implement floating button at `fixed bottom-6 right-6 z-50`; render nothing when `incident` is null
- [ ] 10.3 Implement open/close toggle with `useState(false)` and `AnimatePresence`
- [ ] 10.4 Implement message thread with right-aligned user messages and left-aligned orchestrator responses
- [ ] 10.5 Wire submit to `askIncident(question, incident)` from `@/lib/api`; handle loading and error states
- [ ] 10.6 Import and render `<ActionsChat incident={incident} />` at the root of the dashboard JSX in `console/page.tsx` (outside the grid, at page level)

## 11. Integrations — Remove Composio and Jua Tiles

- [ ] 11.1 Delete the `{ key: "jua", ... }` entry from `SERVICES` in `IntegrationsPanel.tsx`
- [ ] 11.2 Delete the `{ key: "composio", ... }` entry from `SERVICES` in `IntegrationsPanel.tsx`
- [ ] 11.3 Verify 6 remaining tiles reflow in the `sm:grid-cols-2 lg:grid-cols-4` grid without gaps

## 12. Build Verification

- [ ] 12.1 Run `npm run build` in `halyard/` and confirm zero TypeScript or build errors
- [ ] 12.2 Confirm no references to removed `TabKey` type or `TABS` const remain in the codebase
