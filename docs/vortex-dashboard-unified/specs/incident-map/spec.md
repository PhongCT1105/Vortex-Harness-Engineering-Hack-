## ADDED Requirements

### Requirement: IncidentMap is a reusable component that renders geographic points on a globe
The system SHALL provide `halyard/src/components/console/IncidentMap.tsx` exporting a default `IncidentMap` component. It SHALL wrap `react-globe.gl` in a `next/dynamic` import with `{ ssr: false }`. It SHALL accept `points: Array<{ lat: number; lng: number; label: string; severity?: "critical" | "elevated" | "watch" }>` and render each as a colored point on the globe. Autorotation SHALL be disabled. Globe height SHALL be fixed at `h-64`.

Severity color mapping:
- `"critical"` → red (`#ef4444`)
- `"elevated"` → amber (`#f59e0b`)
- `"watch"` → sky blue (`#38bdf8`)
- undefined → accent blue (`#6366f1`)

#### Scenario: Points render with severity colors
- **WHEN** the component receives points with severity values
- **THEN** each point color matches the severity-to-color mapping above

#### Scenario: Empty state renders globe without markers
- **WHEN** no points are passed
- **THEN** the globe renders without any point markers

### Requirement: IncidentMap is embedded in the Ask Incident section
`PromptChatPanel` SHALL render `IncidentMap` when `incident` is non-null, placed below the message list and above the suggested-question chips. Points SHALL be derived from:
- `incident.weather.affected_countries` mapped via a static `CENTROIDS` record to lat/lng, severity from `incident.weather.risk_level`
- `incident.impact.shipments` mapped to country centroids, severity from `risk_score` (≥0.7 → critical, ≥0.5 → elevated, else watch)

#### Scenario: Map appears with active incident
- **WHEN** an incident is loaded in PromptChatPanel
- **THEN** the incident map renders with at least the weather-affected country points

#### Scenario: Map absent when no incident
- **WHEN** `incident` is null
- **THEN** no map element is rendered in PromptChatPanel

### Requirement: IncidentMap is embedded in the Supply Weather section
`ConsolePage` SHALL render `IncidentMap` below the weather assessment content (within the Supply Weather section of row 1 left), when `incident` is non-null. Points SHALL be derived from `incident.weather.affected_countries`. If `supplyWeather` is loaded, `supplyWeather.countries` SHALL also contribute points with severity from `risk_level` (`severe`/`high` → critical, `watch` → watch, else elevated).

#### Scenario: Supply Weather map shows affected countries
- **WHEN** an incident is active on the dashboard
- **THEN** the Supply Weather section shows the map with affected country markers

#### Scenario: Supply weather country risk augments map points
- **WHEN** supplyWeather data is available
- **THEN** supply weather country risk entries appear as additional points on the Supply Weather map
