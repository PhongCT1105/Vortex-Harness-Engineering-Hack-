## MODIFIED Requirements

### Requirement: Integrations panel omits Composio and Jua tiles
The `SERVICES` array in `IntegrationsPanel.tsx` SHALL NOT contain entries with `key: "composio"` or `key: "jua"`. Both entries SHALL be deleted. The remaining tiles SHALL reflow in the existing `sm:grid-cols-2 lg:grid-cols-4` grid without any layout adjustments.

#### Scenario: Composio tile absent
- **WHEN** the Integrations section is visible on the dashboard
- **THEN** no tile labeled "Composio" is rendered

#### Scenario: Jua tile absent
- **WHEN** the Integrations section is visible on the dashboard
- **THEN** no tile labeled "Jua" is rendered

#### Scenario: Remaining tiles reflow cleanly
- **WHEN** two tiles are removed
- **THEN** the remaining 6 tiles fill the grid without empty cells or layout breaks
