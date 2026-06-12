# StormOps — Demo Recording Script

Run through this in order while screen-recording the console (`/console`) and
the supply-chain globe (`/supply-chain`). Each beat maps to a UI section so
you can pause/click as you talk. Aim for ~3-4 minutes total.

---

## 0. Cold open (homepage `/`)

> "This is StormOps — an autonomous incident-response agent for supply chains.
> When severe weather threatens a supplier, StormOps detects it, figures out
> what's exposed, decides what to do, and either acts automatically or asks a
> human for approval — all in one pipeline."

Click **Open console**.

---

## 1. Map the supply chain (`/supply-chain`)

> "First, here's the supply chain itself. Every node on this globe is a real
> supplier — country, component, value, and how critical it is to the final
> product — flowing into our assembly plant."

- Rotate/zoom the globe a little.
- Click 1-2 supplier nodes to show the detail card (value, criticality, node id).

> "You can upload your own CSV to remap this for any product — I'll load the
> demo data we already have."

Click **Open console** (top right) to head back.

---

## 2. Trigger the pipeline (`#trigger`)

> "This is Mission Control. It runs the full agent pipeline end-to-end:
> weather → impact → mitigation → reasoning → comms and Slack — and it
> auto-refreshes every four hours on its own."

- Point at the scenario textarea and the preset **scenario buttons**.

> "I can pick a trigger event — say, a storm system moving across these
> supplier countries — or write my own."

Click a scenario chip, then click **Run pipeline**.

> "Hitting run kicks off the whole chain live."

---

## 3. Weather & impact assessment (`#assessment`)

> "First stop: weather risk. StormOps pulls live conditions — wind,
> precipitation, severity — and classifies the risk level."

- Point at risk level badge (moderate / high / severe) and wind/precip numbers.

> "From there it cross-references our supply chain map to figure out exactly
> which shipments and suppliers fall inside the affected zone, and how much
> dollar value is exposed."

- Point at shipment list / exposure numbers.

---

## 4. Pipeline & reasoning (`#pipeline`)

> "This is the reasoning trace — the actual agent steps. You can see each
> stage: weather detected, impact assessed, actions generated, and the
> model's executive summary explaining *why* it classified this the way it
> did."

- Scroll through the `PipelineFlow` steps.
- Point at the model badge (Claude / DeepSeek / rules) and confidence score.

> "Everything here is grounded — the model isn't guessing, it's reasoning
> over the real weather and shipment data we just pulled."

---

## 5. Actions & approvals (`#actions`)

> "Based on that reasoning, the agent proposes mitigations — reroute a
> shipment, switch to a backup supplier, expedite a replacement part."

- Point at **auto-executed** actions (green) vs **pending approval** (amber).

> "Low-risk, low-value actions get executed automatically. Anything above
> our risk or dollar threshold stops here and waits for a human to approve
> or reject — that's the approval gate."

Click **Approve** (or **Reject**) on one pending action.

> "Once approved, it dispatches through Slack and email automatically."

---

## 6. Ask the incident (`#ask`)

> "Now I can just ask the incident questions in plain language."

- Click one of the suggested questions (e.g. *"Which part of the supply chain
  is damaged?"*).

> "The answer is grounded in the same payload — weather, impact, and the
> ClickHouse audit trail — and it comes back with this OpenUI damage map: the
> weather zone, the affected supplier lane, and the factory's recovery plan,
> with severity, value at risk, and the priority order for fixing it."

- Point at the severity gauge, stat tiles, and recovery plan list.

---

## 7. Audit & integrations (`#audit`)

> "Finally, everything that just happened is logged — every agent decision,
> every Slack message, every approval — captured as ClickHouse audit events
> for full traceability."

- Scroll the audit log / integration status badges (Jua, ClickHouse, Slack,
  Anthropic/DeepSeek).

---

## Close

> "So in one pipeline run: detect the storm, assess the damage, reason about
> priorities, act automatically where it's safe, and escalate to a human
> where it isn't — all fully auditable. That's StormOps."
