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
- Map-style building layout using OSU-style dark building footprints with orange hover emphasis.
- Building hover/focus enlargement.
- Building-to-room drill-down.
- Mock room status, schedule, devices, ServiceNow incidents, and connector health.
- Quick filters.
- Mock tool actions.
- Mock action/audit logging.
- First-run guided tour.

## What This Version Does Not Do Yet

- No real APIs.
- No real Hardware IP data.
- No backend service.
- Public `map.oregonstate.edu` provides building/location data, not the internal Presentation Support room inventory.
- No Microsoft Entra SSO.
- No real ServiceNow ticket creation.
- No real WattBox, Fusion, ScreenConnect, 25Live, or SharePoint calls.

## Version Archive

- `archive/v1-static-clickable-mock` - first static clickable dashboard mock.
- `archive/v1.1-tour-and-building-name-fixes` - fixed guided tour dismissal and corrected mock building names/codes.
- `archive/v1.2-real-osu-map-buildings` - replaced schematic grid with real public OSU building footprints.
- `archive/v1.3-pan-zoom-functional-map` - rebuilt the map as a functional pan/zoom tool.

## Map Data Source

- `map.oregonstate.edu` public Concept3D map, map ID `2243`.
- Buildings category ID `89919`.
- Public API shape used for this mock: `https://api.concept3d.com/categories/89919?map=2243&children`.
- Building data was captured on 2026-05-30.
