## ADDED Requirements

### Requirement: ActionsChat is a fixed bottom-right floating panel on the dashboard
`halyard/src/components/console/ActionsChat.tsx` SHALL render a floating chat button fixed at `bottom-6 right-6` with `z-50`. Clicking the button SHALL open a chat panel (~400px wide, ~500px tall) with an input field and message thread. The panel SHALL be toggled with `AnimatePresence`. It SHALL not render at all when `incident` is null.

#### Scenario: Floating button visible when incident is active
- **WHEN** an incident has been run and is available
- **THEN** the floating chat-bubble button is visible in the bottom-right of the viewport

#### Scenario: No floating button without an incident
- **WHEN** no incident is active
- **THEN** the floating button does not appear

#### Scenario: Panel opens on button click
- **WHEN** the user clicks the floating chat button
- **THEN** the chat panel opens with a message thread and input field

#### Scenario: Panel closes on X button click
- **WHEN** the panel is open and the user clicks the close button
- **THEN** the panel collapses back to the floating button

### Requirement: ActionsChat submits questions to the existing POST /chat endpoint
The panel SHALL call `askIncident(question, incident)` (from `@/lib/api`) on form submit. The response `answer` SHALL be appended to the thread. The input SHALL be disabled while a request is in flight. An error message SHALL display below the thread if the request fails.

#### Scenario: Answer appended after successful request
- **WHEN** the user submits a question
- **THEN** the orchestrator answer appears in the thread after the request resolves

#### Scenario: Loading state during request
- **WHEN** a request to /chat is in flight
- **THEN** the input is disabled and a "Thinking…" placeholder appears in the thread

#### Scenario: Error shown on failure
- **WHEN** the /chat endpoint returns an error
- **THEN** a short error message appears below the thread; the input re-enables

### Requirement: ActionsChat is rendered inside the dashboard
`ConsolePage` SHALL import and render `<ActionsChat incident={incident} />` at the end of the dashboard JSX (outside the grid, at the page root level) so it is fixed to the viewport regardless of scroll position.

#### Scenario: Chat panel accessible from any scroll position
- **WHEN** the user scrolls to the bottom of the dashboard
- **THEN** the floating chat button remains visible in the bottom-right corner
