## Why

The current console uses a sidebar-tab architecture (`ConsoleShell`) that splits related information across 8 separate pages, forcing operators to context-switch during an active incident. A single scrollable dashboard surfaces all mission-critical data simultaneously — weather, pipeline state, reasoning, actions, and the chat interface — without navigation overhead. The 8 UI polish changes from the prior proposal are applied within this new layout rather than the old tab structure.

## What Changes

**PART 1 — Layout restructuring (foundation)**
- Replace the tab-based `ConsoleShell` with a single scrollable `DashboardPage` layout
- Grid arrangement:
  - Row 1: Supply Weather (left col) | Pipeline (right col)
  - Row 2: Agent Reasoning (left col) | Actions & Approvals (right col)
  - Row 3: Ask Incident (left col, full or spanning)
  - Row 4: Audit Log (full width, collapsed by default)
  - Row 5: Integrations (full width, bottom)
- Remove sidebar nav items and tab routing for these sections
- `ConsoleShell` is replaced or hollowed out — the single page uses a minimal fixed header with the model badge and run trigger only

**PART 2 — UI improvements applied within the new layout**
- Pipeline (row 1 right): add inline one-sentence help text per node
- Ask Incident chat input (row 3 left): CSS gradient border, blue-to-purple
- Ask Incident (row 3 left): interactive world map plotting supply chain damage points with severity coding
- Supply Weather (row 1 left): reuse map component to visualize affected geographic areas below weather content
- Supply Weather (row 1 left): simplify Impact title from "Impact — N suppliers, N ..." to "Impact"
- Actions (row 2 right): promote Pending Approval to top; move Auto-Executed into collapsible, collapsed by default
- Actions (row 2 right + fixed viewport): chatbot agent panel fixed bottom-right, wired to existing `POST /chat`
- Integrations (row 5): remove Composio and Jua tiles, reflow remaining

## Capabilities

### New Capabilities

- `unified-dashboard-layout`: Single scrollable page replacing the tab-based `ConsoleShell`; renders all sections in a fixed grid layout
- `incident-map`: Reusable interactive world map component (using `react-globe.gl`, already installed) that plots geographic points with severity color coding; embedded in both Ask Incident and Supply Weather sections
- `actions-chatbot`: Fixed bottom-right floating chat panel on the dashboard, wired to the existing `/chat` endpoint, for plain-language explanation of pending approvals
- `gradient-chat-input`: CSS gradient border wrapper for the Ask Incident chat input field
- `pipeline-help-text`: Inline one-sentence help text per pipeline node

### Modified Capabilities

- `actions-approvals-layout`: Reordered to Pending Approval first, Auto-Executed in collapsible below
- `integrations-panel`: Composio and Jua tiles removed
- `impact-section-title`: Title string simplified to "Impact"

## Impact

- **Primary file replaced/restructured**: `halyard/src/app/console/page.tsx` (tab-dispatch logic removed, replaced with stacked grid layout)
- **Modified**: `halyard/src/components/console/ConsoleShell.tsx` (sidebar and tab nav stripped or bypassed; header shell retained for branding/status slot)
- **Modified**: `halyard/src/components/console/PipelineFlow.tsx` (help text)
- **Modified**: `halyard/src/components/console/PromptChatPanel.tsx` (gradient input, map embed)
- **Modified**: `halyard/src/components/console/IntegrationsPanel.tsx` (tile removal)
- **New files**: `halyard/src/components/console/IncidentMap.tsx`, `halyard/src/components/console/ActionsChat.tsx`
- **Dependencies**: `react-globe.gl` already in `halyard/package.json` — no new packages required
- **Backend**: No new endpoints needed. The existing `POST /chat` serves the Actions chatbot.

---

**Backend change flag (none required):** The existing `POST /chat` endpoint in `backend/main.py` accepts an incident payload and question and returns a plain-language answer. The Actions chatbot will call this via the existing `askIncident()` API function in `halyard/src/lib/api.ts`. No backend modification is needed.
