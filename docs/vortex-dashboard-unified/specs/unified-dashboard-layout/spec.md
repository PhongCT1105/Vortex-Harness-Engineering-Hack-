## ADDED Requirements

### Requirement: All console sections render on a single scrollable page
The `ConsolePage` component SHALL render all sections — Supply Weather, Pipeline, Agent Reasoning, Actions & Approvals, Ask Incident, Audit Log, and Integrations — on one scrollable page without tab-based navigation. No `tab` state, no conditional per-tab rendering, no sidebar nav items for these sections.

#### Scenario: All sections visible without navigation
- **WHEN** the user loads the console page
- **THEN** all sections are present in the DOM and reachable by scrolling, with no tab interaction required

#### Scenario: No sidebar tab buttons rendered
- **WHEN** the console page is rendered
- **THEN** the sidebar (if any) does not contain navigation buttons for Overview, Supply Weather, Pipeline, Reasoning, Ask Incident, Actions, Audit, or Integrations

### Requirement: Dashboard grid layout matches the specified arrangement
The page SHALL use a two-column CSS grid at `lg` breakpoints with the following section placement:
- Row 1: Supply Weather (left) | PipelineFlow (right)
- Row 2: AgentOutputPanel (left) | Actions & Approvals (right)
- Row 3: PromptChatPanel (full width, `lg:col-span-2`)
- Row 4: AuditLog (full width, collapsed by default)
- Row 5: IntegrationsPanel (full width)

StatCards SHALL appear above the grid as a full-width header row.

#### Scenario: Two-column layout at large breakpoint
- **WHEN** the viewport is ≥1024px wide
- **THEN** Supply Weather and Pipeline appear side by side in row 1; Agent Reasoning and Actions appear side by side in row 2

#### Scenario: Single-column stacked on mobile
- **WHEN** the viewport is <1024px wide
- **THEN** all sections stack in a single column in document order

### Requirement: ConsoleShell is reduced to a header-only wrapper
`ConsoleShell` SHALL retain only the fixed top header (branding, page title, `statusSlot`). The sidebar nav, mobile tab bar, and `active`/`onChange` props SHALL be removed. The `TABS` const and `TabKey` type SHALL be removed from `ConsoleShell.tsx`.

#### Scenario: Header renders with branding and status slot
- **WHEN** the dashboard renders
- **THEN** the StormOps brand name, page title, and model badge (statusSlot) appear in a fixed top header

#### Scenario: No sidebar renders
- **WHEN** the dashboard renders at any viewport width
- **THEN** no left-sidebar navigation panel is present in the DOM
