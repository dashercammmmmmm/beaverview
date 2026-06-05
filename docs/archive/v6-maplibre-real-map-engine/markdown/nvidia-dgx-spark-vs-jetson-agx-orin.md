# Research Brief: NVIDIA DGX Spark Vs Jetson AGX Orin

## Recommendation

For the OSU Presentation Support AI Chat Bot, choose **NVIDIA DGX Spark** as the local model host.

The earlier "Orion" reference has been corrected to **NVIDIA Jetson AGX Orin**. Jetson AGX Orin is strong hardware, but it is designed primarily for embedded edge AI, robotics, sensors, and computer vision. This project needs a local assistant platform for chat, retrieval, ticket drafting, and future dashboard-aware guidance. DGX Spark is the better fit.

## Why DGX Spark Fits Better

DGX Spark is positioned by NVIDIA as a compact desktop AI computer for AI development, deployment, fine-tuning, and inference. NVIDIA lists 128 GB unified memory, 20-core Arm CPU, Blackwell GPU architecture, 1 PFLOP FP4-class AI performance, and support for AI models up to 200B parameters depending on configuration.

Those traits matter for this use case because the AI Chat Bot needs:

- Local LLM inference.
- Room-context prompt assembly.
- ServiceNow ticket drafting.
- SharePoint knowledge retrieval.
- Multi-turn troubleshooting conversations.
- Enough memory headroom to test useful assistant models without immediately outgrowing the device.

## Where Jetson AGX Orin Fits

Jetson AGX Orin is positioned by NVIDIA for edge AI, robotics, autonomous machines, generative AI at the edge, and computer vision. The AGX Orin technical brief lists 32 GB and 64 GB module options, up to 275 TOPS INT8 AI performance, integrated camera/sensor I/O, and low power envelopes.

That makes Orin a good future option for:

- Room-local sensors.
- Camera-based status detection.
- Local edge appliances.
- Computer vision experiments.
- Embedded AV monitoring devices.

It should not be treated as the next step up from DGX Spark for the dashboard AI assistant. If DGX Spark is not enough, the next evaluation should be a larger NVIDIA workstation or server-class system.

## Comparison

| Criterion | DGX Spark | Jetson AGX Orin | Better Fit |
| --- | --- | --- | --- |
| Primary purpose | Desktop AI computer for model development, deployment, fine-tuning, and inference. | Edge AI module/developer kit for robotics, autonomous machines, and vision. | DGX Spark |
| Memory | 128 GB LPDDR5x unified memory. | 32 GB or 64 GB LPDDR5. | DGX Spark |
| AI performance | Up to 1 PFLOP FP4 / 1,000 TOPS-class AI compute. | Up to 275 TOPS INT8. | DGX Spark |
| Model support | NVIDIA states support for AI models up to 200B parameters. | Optimized edge inference and sensor workloads. | DGX Spark |
| Deployment role | Local AI service host for chat, RAG, and ticket drafting. | Embedded device or edge appliance. | DGX Spark |
| Future use | Primary AI Chat Bot pilot host. | Optional future room-edge device. | Both, but for different jobs |

## Decision

Use this wording in leadership and technical materials:

> The AI Chat Bot should use DGX Spark as the first local model host. Jetson AGX Orin is not recommended as the primary host for this use case; it is better suited to future edge AI or room-local sensing projects. If DGX Spark does not meet concurrency or model-size needs, evaluate larger NVIDIA workstation or server-class hardware.

## Sources

- NVIDIA DGX Spark product/specification page: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
- NVIDIA DGX Spark User Guide hardware overview: https://docs.nvidia.com/dgx/dgx-spark/hardware.html
- NVIDIA Jetson AGX Orin product page: https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/
- NVIDIA Jetson AGX Orin Series Technical Brief: https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf

