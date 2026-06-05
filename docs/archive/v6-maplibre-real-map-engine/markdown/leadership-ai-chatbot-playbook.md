# Leadership Playbook: AI Chat Bot For Support And ServiceNow Integration

## Executive Summary

The **AI Chat Bot** is a separate project that complements the OSU Presentation Support Dashboard. The Dashboard gives technicians visual command of rooms and tools; the AI Chat Bot gives them guided troubleshooting, context-aware support, and high-quality ServiceNow ticket drafts.

The AI should feel like part of the same ecosystem. When a technician opens a room, the bot should already understand the room, current status, recent dashboard actions, schedule context, known devices, SharePoint training references, and relevant ServiceNow history.

The recommended deployment path uses local models on **DGX Spark first**. The earlier reference to "Orion" is corrected to **NVIDIA Jetson AGX Orin**. Jetson AGX Orin is valuable edge AI hardware, but it is not the better primary host for this AI chat use case.

## Value Proposition

The AI Chat Bot improves support quality without replacing human judgment.

Primary value:

- Helps student workers follow consistent troubleshooting workflows.
- Provides real-time support during calls.
- Turns room status, recent actions, and call notes into structured ServiceNow drafts.
- Reduces incomplete or inconsistent ticket documentation.
- Surfaces relevant SharePoint training materials.
- Preserves human approval for disruptive or sensitive actions.
- Creates a training layer for new technicians through guided onboarding and contextual help.

## How It Complements The Dashboard

```mermaid
flowchart LR
    Dashboard[Presentation Support Dashboard] --> Context[Room Context API]
    Context --> AI[AI Chat Bot]
    SharePoint[SharePoint Training Docs] --> AI
    Logs[Recent Actions] --> AI
    SN[ServiceNow] <--> Draft[Ticket Draft Workflow]
    AI --> Draft
    AI --> Tech[Technician Review]
```

The Dashboard remains the source of operational truth. The AI consumes approved dashboard context rather than independently scraping tools or exposing credentials.

Example technician workflow:

1. Technician opens KAd 101 in the Dashboard.
2. AI receives room status, device inventory, active class/event, recent incidents, and recent actions.
3. Technician describes the caller's issue.
4. AI guides verification steps.
5. AI recommends next actions, with power cycling treated as a last-resort step.
6. AI drafts ServiceNow documentation using Call Documentation templates.
7. Technician reviews, edits, and submits the ticket.

## Local AI Direction

Recommended baseline:

- **DGX Spark first** for local model hosting.
- **Do not use Jetson AGX Orin as the primary AI chat host** for this project.
- Use Jetson AGX Orin only if OSU later needs an edge appliance for room-local computer vision, sensor processing, or constrained on-device inference.
- If DGX Spark cannot meet concurrency or model-size needs, scale up to a larger workstation/server-class NVIDIA system rather than moving to Jetson AGX Orin.
- Keep sensitive operational context local where practical.
- Avoid sending hardware IP data or sensitive incident details to external AI systems unless explicitly approved.

This approach aligns with cybersecurity expectations and gives OSU more control over model behavior, logs, and data flow.

## DGX Spark Vs Jetson AGX Orin Recommendation

Recommendation: **choose NVIDIA DGX Spark for the AI Chat Bot pilot and local model host**.

| Criterion | DGX Spark | Jetson AGX Orin | Fit For This Project |
| --- | --- | --- | --- |
| Primary NVIDIA positioning | Desktop AI computer for prototyping, deploying, fine-tuning, and inference with large AI models. | Edge AI/robotics module and developer kit for autonomous systems, robotics, vision, and sensor-heavy workloads. | Dashboard chat/ticket drafting aligns with DGX Spark. |
| Memory | 128 GB unified memory. | 32 GB or 64 GB LPDDR5 depending on module. | DGX Spark has much more headroom for local LLMs and retrieval. |
| AI performance | Up to 1 PFLOP FP4 / 1,000 TOPS-class AI compute. | Up to 275 TOPS INT8 for AGX Orin 64GB. | DGX Spark is better for modern local LLM serving. |
| Model support | NVIDIA states support for AI models up to 200B parameters, depending on precision/configuration. | Better suited to optimized edge inference than larger assistant-style LLM workloads. | DGX Spark is the practical baseline. |
| Operational fit | Desktop/server-room friendly local AI host. | Embedded/edge device requiring Jetson-specific deployment expectations. | DGX Spark is easier to treat as the local AI service host. |

Sources used:

- NVIDIA DGX Spark product/specification page: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
- NVIDIA DGX Spark User Guide hardware overview: https://docs.nvidia.com/dgx/dgx-spark/hardware.html
- NVIDIA Jetson AGX Orin product page: https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/
- NVIDIA Jetson AGX Orin Series Technical Brief: https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf

## ServiceNow Ticket Draft Workflow

The bot should draft tickets, not silently submit them.

Draft fields:

- caller ONID
- building
- room
- category
- assignment group
- short description
- troubleshooting notes
- affected device
- Call Documentation template fields
- current room status snapshot
- recent dashboard actions
- relevant 25Live/Fusion schedule context
- related open incidents and five recent closed incidents

Human review is required before submission. The technician should be able to edit the draft and decide whether it becomes a ServiceNow ticket.

## Security, Compliance, And Risk Posture

Required controls:

- Use dashboard APIs as the approved data source.
- Keep service credentials out of the browser and out of prompts.
- Redact unnecessary personal data.
- Log AI usage according to approved OSU policy.
- Require human confirmation before disruptive recommendations such as power cycling.
- Keep prompt/response retention limited and policy-aligned.
- Review FERPA, cybersecurity, data classification, and ServiceNow data handling requirements.

The AI should learn from structured technician feedback, not uncontrolled self-modification. Feedback can be stored as ratings, comments, accepted/rejected recommendations, and corrected ticket drafts.

## Training And Adoption

The AI Chat Bot should support both live troubleshooting and onboarding.

Recommended training features:

- First-time user tour.
- Contextual explanations of Dashboard sections.
- Guided call-handling mode for student workers.
- Common issue workflows.
- "Why am I recommending this?" explanations.
- Feedback buttons for helpful/not helpful recommendations.
- Links to relevant SharePoint training PDFs.

This makes the tool feel supportive rather than supervisory.

## Screenshot Placeholders For Future Prototype

Add screenshots to the HTML/PDF version after the AI mock exists:

- AI assistant opened from a room.
- Guided troubleshooting flow.
- Verification-first recommendation.
- SharePoint training document suggestion.
- ServiceNow draft before technician review.
- Technician edit/review screen.
- Feedback capture after a recommendation.

## Timeline And Staffing Recommendation

| Phase | Duration | Outcome |
| --- | ---: | --- |
| 1. AI workflow design | 1-2 weeks | Define supported scenarios, ticket templates, safety rules, and required context. |
| 2. Local model baseline | 2-4 weeks | DGX Spark model serving, basic chat UI, and test prompts. |
| 3. Dashboard context integration | 2-3 weeks | AI consumes room/status/action context from Dashboard APIs. |
| 4. ServiceNow draft workflow | 2-4 weeks | Draft tickets from guided troubleshooting and templates. |
| 5. SharePoint knowledge connection | 2-4 weeks | Link or retrieve approved training materials. |
| 6. Pilot and tuning | ongoing | Improve prompts, workflows, and documentation quality from technician feedback. |

Recommended staffing:

- Product owner.
- AV support subject matter expert.
- AI/application developer.
- ServiceNow administrator.
- SharePoint/knowledge owner.
- Cybersecurity reviewer.
- Technician/student pilot group.

## Success Metrics

- More complete ServiceNow tickets.
- Less time spent writing ticket notes.
- Reduced escalation from student workers for common issues.
- Faster troubleshooting during live calls.
- Higher consistency in verification steps.
- Technician trust and voluntary usage.
- Reduced repeated mistakes in support documentation.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| AI gives unsafe recommendation | Verification-first prompts, human confirmation, power cycle as last resort. |
| Sensitive data in prompts/logs | Local model hosting, redaction, retention policy, approved context API. |
| Poor ticket quality | Use templates, technician review, feedback loops, scenario testing. |
| Over-trust by student workers | Explain reasoning, require review, provide escalation guidance. |
| Hardware capacity limits | DGX Spark baseline, monitor concurrency and latency, then scale to a larger NVIDIA workstation/server if needed. |
| Knowledge drift | Use approved SharePoint sources and regular content review. |

## Approval Decisions Needed

Leadership should approve:

- DGX Spark as first local model target.
- Human-reviewed ServiceNow drafts as the default workflow.
- Data retention and logging standards for AI prompts/responses.
- Initial support scenarios for pilot.
- SharePoint knowledge sources approved for AI use.
- Cybersecurity review path before production use.

## Next Steps After Playbook Approval

1. Select pilot troubleshooting scenarios.
2. Gather Call Documentation templates.
3. Confirm DGX Spark availability and model-serving approach.
4. Define Dashboard context API contract.
5. Build AI chat mock flow after Dashboard mock is approved.
6. Pilot ServiceNow ticket draft workflow with technicians and student workers.

## Open Questions

- Which local model family should be tested first on DGX Spark?
- What prompt/response retention is allowed by OSU policy?
- Which ServiceNow assignment groups and categories should be defaulted?
- Which SharePoint folders are approved for AI retrieval?
