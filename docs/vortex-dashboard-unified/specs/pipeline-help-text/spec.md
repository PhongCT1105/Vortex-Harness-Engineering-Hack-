## ADDED Requirements

### Requirement: Each pipeline node card displays one-sentence help text
`PipelineFlow.tsx` SHALL add a `helpText: string` field to the `FlowNode` type and populate it for all 5 entries in `NODES`. The text SHALL be rendered inside the node card as a third line (`<p className="mt-0.5 text-[10px] leading-tight text-text-muted">`) below the existing `sublabel` line. The text SHALL be visible in all node states without hover interaction.

Help text values:
- **Trigger**: "Ingests the natural-language event and starts the agent pipeline."
- **Weather agent**: "Fetches live Jua / Open-Meteo conditions and scores geographic risk."
- **Impact agent**: "Traverses the supplier graph to find shipments inside the exposure zone."
- **Mitigation agent**: "Ranks rerouting, expediting, and substitution options by risk and value."
- **Comms agent**: "Sends approved notifications via Slack and email through Composio."

#### Scenario: Help text visible in idle state
- **WHEN** no incident is running
- **THEN** all five node cards show their help text in muted small type

#### Scenario: Help text visible in active and done states
- **WHEN** an incident is running or complete
- **THEN** help text remains visible in active (pulsing) and done (green) node states

#### Scenario: Text fits within node minimum width
- **WHEN** the pipeline is at minimum width (9.5rem per node)
- **THEN** help text wraps without causing horizontal scroll in the stepper container
