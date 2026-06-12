## MODIFIED Requirements

### Requirement: Actions section renders Pending Approval first, Auto-Executed in a collapsible below
The Actions & Approvals section in `ConsolePage` (now a grid cell in row 2 right, not a tab) SHALL use a `flex flex-col gap-4` layout. The Pending Approval block SHALL appear first. The Auto-Executed block SHALL be wrapped in a collapsible using `useState(false)` (collapsed by default) and `AnimatePresence`, following the same `CaretDown` toggle pattern used in `AuditLog`. The current `grid sm:grid-cols-2` layout SHALL be removed.

#### Scenario: Pending Approval renders at top
- **WHEN** the dashboard is loaded with an active incident
- **THEN** the Pending Approval section is the first element in the Actions column

#### Scenario: Auto-Executed collapsed by default
- **WHEN** the dashboard first renders with auto-executed actions present
- **THEN** the Auto-Executed list is not visible; only its collapsed header is shown

#### Scenario: Expanding Auto-Executed
- **WHEN** the user clicks the Auto-Executed header toggle
- **THEN** the list animates open revealing all auto-executed items

#### Scenario: Collapsing after expand
- **WHEN** the Auto-Executed section is open and the user clicks the header again
- **THEN** the list animates closed
