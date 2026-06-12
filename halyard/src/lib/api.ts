const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Weather = {
  affected_countries: string[];
  wind_kmh: number;
  precipitation_mm: number;
  temperature_c: number;
  severity: number;
  risk_level: "moderate" | "high" | "severe";
  source: "jua" | "claude" | "mock";
};

export type Shipment = {
  shipment_id: string;
  supplier_id: string;
  backup_supplier_id: string;
  country: string;
  component: string;
  value_usd: number;
  criticality: number;
  risk_score: number;
};

export type Impact = {
  affected_suppliers: number;
  at_risk_shipments: number;
  shipments: Shipment[];
};

export type Action = {
  id: string;
  shipment_id: string;
  action: string;
  value_usd: number;
  risk_score: number;
  requires_approval: boolean;
  status?: string;
  channel?: string;
  sent?: boolean;
  body?: string;
};

export type Incident = {
  incident_id: string;
  weather: Weather;
  impact: Impact;
  auto_executed: Action[];
  pending_approval: Action[];
};

export type AgentEventRow = {
  ts: number;
  incident_id: string;
  kind: string;
  payload: unknown;
};

export type IntegrationStatus = {
  jua: boolean;
  anthropic: boolean;
  deepseek: boolean;
  clickhouse: boolean;
  airbyte: boolean;
  slack: boolean;
  active_model: "claude" | "deepseek";
};

export type IncidentChatResponse = {
  answer: string;
  openui_lang: string;
  suggested_questions: string[];
};

export type ConfigKeys = {
  JUA_API_KEY?: string;
  ANTHROPIC_API_KEY?: string;
  DEEPSEEK_API_KEY?: string;
  ACTIVE_MODEL?: string;
  CLICKHOUSE_HOST?: string;
  CLICKHOUSE_PORT?: string;
  CLICKHOUSE_USER?: string;
  CLICKHOUSE_PASSWORD?: string;
  CLICKHOUSE_DATABASE?: string;
  AIRBYTE_API_KEY?: string;
  SLACK_WEBHOOK_URL?: string;
  SLACK_CHANNEL?: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`${options?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function runIncident(event: string): Promise<Incident> {
  return request<Incident>("/run", {
    method: "POST",
    body: JSON.stringify({ event }),
  });
}

export function approveAction(action: Action): Promise<{ channel: string; sent: boolean; body: string }> {
  return request("/approve", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export function askIncident(question: string, incident: Incident): Promise<IncidentChatResponse> {
  return request<IncidentChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ question, incident }),
  });
}

export function getEvents(): Promise<AgentEventRow[]> {
  return request<AgentEventRow[]>("/events");
}

export function getConfig(): Promise<IntegrationStatus> {
  return request<IntegrationStatus>("/config");
}

export function setConfig(keys: ConfigKeys): Promise<IntegrationStatus> {
  return request<IntegrationStatus>("/config", {
    method: "POST",
    body: JSON.stringify(keys),
  });
}
