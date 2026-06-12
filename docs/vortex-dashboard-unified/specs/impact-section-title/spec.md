## MODIFIED Requirements

### Requirement: Impact section heading displays "Impact" only
The `<h2>` element heading the Impact section in `console/page.tsx` SHALL display the static string `"Impact"`. The current interpolated content `Impact — {incident.impact.affected_suppliers} suppliers, {incident.impact.at_risk_shipments} shipments at risk` SHALL be replaced with the literal text `Impact`. No other changes to the Impact section content, table, or surrounding markup are permitted.

#### Scenario: Simplified heading renders
- **WHEN** an incident is active and the Impact section is visible
- **THEN** the section heading reads "Impact" with no counts appended

#### Scenario: Impact section data unchanged
- **WHEN** the title is simplified
- **THEN** all table rows, columns, and shipment data in the Impact section remain identical to before
