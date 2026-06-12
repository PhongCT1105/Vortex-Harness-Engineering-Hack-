const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Weather = {
  affected_countries: string[];
  wind_kmh: number;
  precipitation_mm: number;
  temperature_c: number;
  severity: number;
  risk_level: "moderate" | "high" | "severe";
  source: "jua" | "jua+event" | "open-meteo" | "open-meteo+event" | "rules";
  confidence?: number;
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
  product?: string;
  weather: Weather;
  impact: Impact;
  orchestration?: {
    source: "claude" | "deepseek" | "rules";
    executive_summary: string;
    damaged_nodes: Array<{
      node: string;
      reason: string;
      severity: "watch" | "elevated" | "critical";
    }>;
    priority_order: string[];
    operator_questions: string[];
    route_weather_findings?: string[];
    tool_calls?: unknown[];
    confidence: number;
  };
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
  weatherapi?: boolean;
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
  JUA_FORECAST_URL?: string;
  WEATHERAPI_KEY?: string;
  ANTHROPIC_API_KEY?: string;
  ANTHROPIC_MODEL?: string;
  DEEPSEEK_API_KEY?: string;
  DEEPSEEK_MODEL?: string;
  ACTIVE_MODEL?: string;
  CLICKHOUSE_HOST?: string;
  CLICKHOUSE_PORT?: string;
  CLICKHOUSE_USER?: string;
  CLICKHOUSE_PASSWORD?: string;
  CLICKHOUSE_DATABASE?: string;
  AIRBYTE_API_KEY?: string;
  AIRBYTE_REPORT_WEBHOOK_URL?: string;
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

export type SupplyChainNode = {
  id: string;
  shipment_id?: string;
  backup_supplier_id?: string;
  name: string;
  country: string;
  lat: number;
  lng: number;
  component: string;
  value_usd: number;
  criticality: number;
};

export type SupplyChainArc = {
  id: string;
  supplier_id: string;
  component: string;
  country: string;
  value_usd: number;
  criticality: number;
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
};

export type AssemblyPlant = {
  name: string;
  city: string;
  country: string;
  lat: number;
  lng: number;
};

export type SupplyChain = {
  product: string;
  assembly: AssemblyPlant;
  nodes: SupplyChainNode[];
  arcs: SupplyChainArc[];
  unresolved_countries: string[];
  total_value_usd: number;
};

export type SupplyChainWeatherCountry = {
  country: string;
  lat: number;
  lng: number;
  supplier_count: number;
  components: string[];
  value_usd: number;
  avg_criticality: number;
  wind_kmh: number;
  precipitation_mm: number;
  temperature_c: number;
  weather_code: number | null;
  severity: number;
  risk_level: "normal" | "watch" | "high" | "severe";
  source: string;
  condition?: string;
  provider_readings?: Array<{
    source: string;
    wind_kmh: number;
    precipitation_mm: number;
    temperature_c: number;
    condition: string;
  }>;
  context: string;
  search: {
    source: "duckduckgo" | "rules";
    query: string;
    summary: string;
    results: Array<{
      title: string;
      url: string;
      snippet: string;
    }>;
  };
};

export type SupplyChainWeather = {
  product: string;
  assembly: AssemblyPlant;
  generated_at: string;
  expires_at: string;
  refresh_seconds: number;
  source: string;
  worst_risk_level: "normal" | "watch" | "high" | "severe";
  max_severity: number;
  countries: SupplyChainWeatherCountry[];
  routes: Array<{
    supplier_id: string;
    component: string;
    country: string;
    value_usd: number;
    criticality: number;
    destination: {
      name: string;
      city: string;
      country: string;
    };
    points: Array<{
      kind: "origin" | "route_midpoint" | "assembly";
      label: string;
      search_name: string;
      lat: number;
      lng: number;
      weather: SupplyChainWeatherCountry;
    }>;
    max_severity: number;
    worst_risk_level: "normal" | "watch" | "high" | "severe";
    worst_point: string;
    context: string;
  }>;
};

export type SupplyChainAutomationReport = {
  source: "claude" | "deepseek" | "rules";
  product: string;
  automation_id: string;
  current_condition: "normal" | "watch" | "high" | "severe";
  executive_summary: string;
  exposure_summary: string[];
  recommended_actions: string[];
  requires_human_attention: boolean;
  urgency: "normal" | "watch" | "urgent";
  confidence: number;
  tool_calls?: unknown[];
};

export type SupplyChainAutomationResult = {
  automation_id: string;
  product: string;
  weather_source: "clickhouse_cached" | "refreshed";
  weather_generated_at: string;
  report: SupplyChainAutomationReport;
  dispatch: {
    airbyte: { configured: boolean; sent: boolean; error?: string };
    slack: { configured: boolean; sent: boolean; channel: string; error?: string };
    body: string;
  };
};

export function getSupplyChain(product?: string): Promise<SupplyChain> {
  const qs = product ? `?product=${encodeURIComponent(product)}` : "";
  return request<SupplyChain>(`/supply-chain${qs}`);
}

export function getSupplyChainWeather(options?: {
  product?: string;
  forceRefresh?: boolean;
}): Promise<SupplyChainWeather> {
  const params = new URLSearchParams();
  if (options?.product) params.set("product", options.product);
  if (options?.forceRefresh) params.set("force_refresh", "true");
  const qs = params.toString();
  return request<SupplyChainWeather>(`/supply-chain/weather${qs ? `?${qs}` : ""}`);
}

export async function uploadSupplyChain(file: File, product: string): Promise<SupplyChain> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("product", product);
  const res = await fetch(`${API_BASE}/supply-chain/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`POST /supply-chain/upload failed: ${res.status}`);
  }
  return res.json();
}

export function runSupplyChainAutomation(options?: {
  product?: string;
  forceRefresh?: boolean;
}): Promise<SupplyChainAutomationResult> {
  return request<SupplyChainAutomationResult>("/automation/supply-chain/report", {
    method: "POST",
    body: JSON.stringify({
      product: options?.product,
      force_refresh: options?.forceRefresh ?? false,
    }),
  });
}
