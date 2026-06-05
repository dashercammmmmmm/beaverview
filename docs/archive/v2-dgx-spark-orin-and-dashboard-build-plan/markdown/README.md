# OSU Presentation Support Platform Playbook Package

This folder contains the living documentation package for the neutral-placeholder **OSU Presentation Support Platform**.

## Project Name Recommendations

Use **OSU Presentation Support Platform** as the neutral placeholder until leadership selects a final name.

Recommended final names:

1. **OSU Presentation Support Command Center** - strongest fit for the map-style operational dashboard.
2. **OSU AV Support Hub** - shorter, approachable, and easy for technicians to remember.
3. **OSU Classroom Support Console** - clear and leadership-friendly, but narrower than the full AV support scope.
4. **OSU SupportLens** - polished brand option, useful if the project grows beyond presentation support.

## Documents

### Markdown Source

- [Leadership Playbook - Dashboard](leadership-dashboard-playbook.md)
- [Technical Playbook - Dashboard](technical-dashboard-playbook.md)
- [Leadership Playbook - AI Chat Bot](leadership-ai-chatbot-playbook.md)
- [Technical Playbook - AI Chat Bot](technical-ai-chatbot-playbook.md)
- [Phased Build Playbook - Dashboard](dashboard-build-phased-playbook.md)
- [Research Brief - DGX Spark vs Jetson AGX Orin](nvidia-dgx-spark-vs-jetson-agx-orin.md)

### HTML Versions

- [Leadership Playbook - Dashboard](html/leadership-dashboard-playbook.html)
- [Technical Playbook - Dashboard](html/technical-dashboard-playbook.html)
- [Leadership Playbook - AI Chat Bot](html/leadership-ai-chatbot-playbook.html)
- [Technical Playbook - AI Chat Bot](html/technical-ai-chatbot-playbook.html)
- [Phased Build Playbook - Dashboard](html/dashboard-build-phased-playbook.html)
- [Research Brief - DGX Spark vs Jetson AGX Orin](html/nvidia-dgx-spark-vs-jetson-agx-orin.html)

## Maintenance Model

The Markdown files are the source of truth. The HTML files should be regenerated after Markdown updates so both versions stay aligned. PDF copies can be exported from the HTML files using Chrome's print-to-PDF workflow.

Regenerate HTML after edits:

```bash
python3 scripts/build_playbook_html.py
```

## Version Archive

Archived versions are kept under `docs/archive/`.

- `v1-initial-package` - first four-playbook package before DGX Spark vs Jetson AGX Orin research.
- `v2-dgx-spark-orin-and-dashboard-build-plan` - current package with NVIDIA research updates and the separate phased dashboard build playbook.

## Source Research

The playbooks synthesize the local research files originally provided for:

- Dashboard architecture and best practices
- OSU campus map and building strategy
- Crestron Fusion API
- 25Live API
- SnapAV/OvrC/WattBox integration
- ScreenConnect integration
- AI chat and future integrations
