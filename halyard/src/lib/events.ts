export type AgentEvent = {
  time: string;
  actor: "monitor" | "reason" | "act" | "human";
  text: string;
};

export const agentEvents: AgentEvent[] = [
  { time: "14:02:11", actor: "monitor", text: "Storm cell detected, Gulf Coast region" },
  { time: "14:02:14", actor: "reason", text: "Cross-referenced 3 suppliers within radius" },
  { time: "14:02:19", actor: "reason", text: "Ranked exposure: Houston freight, 2 ports" },
  { time: "14:02:23", actor: "act", text: "Draft alert generated for #ops-alerts" },
  { time: "14:03:02", actor: "act", text: "Sent to Slack, awaiting approval" },
  { time: "14:04:55", actor: "human", text: "Approved by M. Reyes, Ops Lead" },
];
