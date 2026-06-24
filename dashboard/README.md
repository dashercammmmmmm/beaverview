# OSU Presentation Support Dashboard Mock

This is the Phase 1 static clickable mock for the OSU Presentation Support Platform dashboard.

Open locally:

```text
file:///Users/cam/Documents/New%20project/dashboard/index.html
```

## What This Version Demonstrates

- Desktop-first dashboard layout.
- Campus switching for Corvallis, OSU-Cascades, and Hatfield Marine.
- Smooth campus transition.
- Real building footprint data from `map.oregonstate.edu` / Concept3D Buildings category `89919`.
- Functional map surface with drag-to-pan, wheel zoom, zoom buttons, reset, and clickable building footprints.
- Real MapLibre map engine with OpenStreetMap base tiles, official OSU building footprints, and OSU-style dark/orange building overlay.
- Local MapLibre engine files are vendored under `vendor/maplibre` so the map engine itself does not depend on internet access.
- Building hover/focus enlargement.
- Building-to-room drill-down.
- Mock room status, schedule, devices, ServiceNow incidents, and connector health.
- Generated placeholder rooms for every public OSU map building so every building can be opened during review.
- Quick filters.
- Mock tool actions.
- Mock action/audit logging.
- First-run guided tour.

## What This Version Does Not Do Yet

- No real APIs.
- No real Hardware IP data.
- Generated room entries are placeholders and must be replaced by the secure inventory import.
- No backend service.
- Public `map.oregonstate.edu` provides building/location data, not the internal Presentation Support room inventory.
- No Microsoft Entra SSO.
- No ServiceNow ticket creation from the static dashboard UI yet; the backend has a guarded create endpoint.
- No real WattBox, Fusion, ScreenConnect, 25Live, or SharePoint calls.

## Version Archive

- `archive/v1-static-clickable-mock` - first static clickable dashboard mock.
- `archive/v1.1-tour-and-building-name-fixes` - fixed guided tour dismissal and corrected mock building names/codes.
- `archive/v1.2-real-osu-map-buildings` - replaced schematic grid with real public OSU building footprints.
- `archive/v1.3-pan-zoom-functional-map` - rebuilt the map as a functional pan/zoom tool.
- `archive/v1.4-maplibre-real-map-engine` - replaced custom SVG projection with a real MapLibre map engine and geographic building placement.
- `archive/v1.5-generated-rooms-all-buildings` - restored v1.3 map baseline and added generated placeholder rooms for every mapped building.
- `archive/v1.6-rollback-to-v1.3-pan-zoom` - restored the active dashboard to the v1.3 pan/zoom functional map baseline after later room/map experiments were rejected.
- `archive/v1.7-maplibre-with-all-building-rooms` - restored v1.4 MapLibre map baseline and added generated placeholder rooms for every mapped building.
- `archive/v1.8-local-maplibre-engine` - keeps the v1.7 MapLibre room coverage and vendors MapLibre locally so the engine loads without external CDN access.

## Map Data Source

- `map.oregonstate.edu` public Concept3D map, map ID `2243`.
- Buildings category ID `89919`.
- Public API shape used for this mock: `https://api.concept3d.com/categories/89919?map=2243&children`.
- Building data was captured on 2026-05-30.
- MapLibre engine files are local in this package. OpenStreetMap base tiles still load from the network unless a local tile service is added later.
