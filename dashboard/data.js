window.dashboardData = {
  campuses: [
    {
      id: "corvallis",
      name: "Corvallis",
      subtitle: "Primary support campus",
      connectors: {
        crestron: "ok",
        live25: "ok",
        screenconnect: "degraded",
        wattbox: "mock",
        servicenow: "ok"
      },
      buildings: [
        {
          code: "KAd",
          name: "Kerr Administration Building",
          x: 42,
          y: 48,
          rooms: [
            {
              number: "101",
              type: "Presentation Classroom",
              status: "issue",
              health: 72,
              activeEvent: "Faculty training until 11:50 AM",
              processor: "online",
              display: "standby",
              screenconnect: true,
              wattbox: true,
              hybrid: false,
              stale: false,
              incidents: {
                open: ["INC0012418 - Display source mismatch"],
                closed: ["INC0012392 - Lectern PC restart", "INC0012311 - HDMI adapter replaced"]
              },
              devices: [
                ["Display", "NEC", "P-series", "Sanitized host"],
                ["Control Processor", "Crestron", "CP4", "Sanitized host"],
                ["Lectern PC", "Dell", "OptiPlex", "ScreenConnect"]
              ]
            },
            {
              number: "105",
              type: "Conference Room",
              status: "available",
              health: 96,
              activeEvent: "Available",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: false,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: ["INC0012250 - Camera preset reset"] },
              devices: [["Camera", "PTZOptics", "Move SE", "Sanitized host"]]
            }
          ]
        },
        {
          code: "LINC",
          name: "Learning Innovation Center",
          x: 52,
          y: 32,
          rooms: [
            {
              number: "100",
              type: "Lecture Hall",
              status: "in-use",
              health: 91,
              activeEvent: "BI 211 until 12:20 PM",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: ["INC0012298 - Microphone battery swap"] },
              devices: [["Projector", "Panasonic", "PT-RZ", "Sanitized host"], ["Camera", "AVer", "TR-series", "Sanitized host"]]
            },
            {
              number: "228",
              type: "Active Learning Room",
              status: "available",
              health: 98,
              activeEvent: "Available until 1:00 PM",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Display Array", "LG", "Commercial", "Sanitized host"]]
            }
          ]
        },
        {
          code: "MU",
          name: "Memorial Union",
          x: 35,
          y: 38,
          rooms: [
            {
              number: "208",
              type: "Event Space",
              status: "in-use",
              health: 87,
              activeEvent: "Student org event until 2:00 PM",
              processor: "online",
              display: "on",
              screenconnect: false,
              wattbox: true,
              hybrid: false,
              stale: false,
              incidents: { open: [], closed: ["INC0012380 - Audio routing verified"] },
              devices: [["DSP", "Q-SYS", "Core", "Sanitized host"]]
            }
          ]
        },
        {
          code: "ALS",
          name: "Agricultural & Life Sciences",
          x: 58,
          y: 47,
          rooms: [
            {
              number: "4000",
              type: "Lecture Hall",
              status: "offline",
              health: 48,
              activeEvent: "Class scheduled now",
              processor: "offline",
              display: "unknown",
              screenconnect: false,
              wattbox: true,
              hybrid: true,
              stale: true,
              incidents: { open: ["INC0012422 - Processor not reporting"], closed: ["INC0012332 - Projector lamp warning"] },
              devices: [["Processor", "Crestron", "CP4N", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Dear",
          name: "Dearborn Hall",
          x: 62,
          y: 62,
          rooms: [
            {
              number: "118",
              type: "Classroom",
              status: "available",
              health: 93,
              activeEvent: "Available",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: false,
              hybrid: false,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Display", "NEC", "V-series", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Gilb",
          name: "Gilbert Hall",
          x: 70,
          y: 52,
          rooms: [
            {
              number: "124",
              type: "Classroom",
              status: "issue",
              health: 69,
              activeEvent: "CHEM recitation until 12:00 PM",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: false,
              stale: false,
              incidents: { open: ["INC0012416 - Audio intermittent"], closed: ["INC0012285 - Cable replaced"] },
              devices: [["Microphone Receiver", "Shure", "QLX-D", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Cord",
          name: "Cordley Hall",
          x: 48,
          y: 65,
          rooms: [
            {
              number: "1109",
              type: "Classroom",
              status: "available",
              health: 94,
              activeEvent: "Available",
              processor: "online",
              display: "off",
              screenconnect: false,
              wattbox: false,
              hybrid: false,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Projector", "Epson", "PowerLite", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Bexl",
          name: "Bexell Hall",
          x: 28,
          y: 58,
          rooms: [
            {
              number: "415",
              type: "Classroom",
              status: "in-use",
              health: 89,
              activeEvent: "ECON until 11:20 AM",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: ["INC0012309 - Zoom audio checked"] },
              devices: [["Camera", "Logitech", "Rally", "Sanitized host"]]
            }
          ]
        },
        {
          code: "LSC",
          name: "The LaSells Stewart Center",
          x: 74,
          y: 72,
          rooms: [
            {
              number: "Austin",
              type: "Auditorium",
              status: "available",
              health: 97,
              activeEvent: "Event setup at 3:00 PM",
              processor: "online",
              display: "standby",
              screenconnect: false,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Switcher", "Extron", "IN-series", "Sanitized host"]]
            }
          ]
        },
        {
          code: "KEC",
          name: "Kelley Engineering Center",
          x: 18,
          y: 42,
          rooms: [
            {
              number: "1001",
              type: "Lecture Hall",
              status: "available",
              health: 95,
              activeEvent: "Available",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: ["INC0012211 - USB camera firmware checked"] },
              devices: [["Display", "Samsung", "QMB", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Mlm",
          name: "Milam Hall",
          x: 24,
          y: 24,
          rooms: [
            {
              number: "026",
              type: "Classroom",
              status: "available",
              health: 90,
              activeEvent: "Available",
              processor: "online",
              display: "off",
              screenconnect: true,
              wattbox: false,
              hybrid: false,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Projector", "Panasonic", "Sample", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Nash",
          name: "Nash Hall",
          x: 80,
          y: 27,
          rooms: [
            {
              number: "032",
              type: "Teaching Lab",
              status: "issue",
              health: 76,
              activeEvent: "Lab until 12:50 PM",
              processor: "online",
              display: "on",
              screenconnect: true,
              wattbox: false,
              hybrid: false,
              stale: false,
              incidents: { open: ["INC0012420 - Camera not detected"], closed: [] },
              devices: [["Document Camera", "WolfVision", "Sample", "Sanitized host"]]
            }
          ]
        }
      ]
    },
    {
      id: "cascades",
      name: "OSU-Cascades",
      subtitle: "Bend campus",
      connectors: { crestron: "mock", live25: "ok", screenconnect: "ok", wattbox: "mock", servicenow: "ok" },
      buildings: [
        {
          code: "Tyke",
          name: "Tykeson Hall",
          x: 42,
          y: 46,
          rooms: [
            {
              number: "111",
              type: "Classroom",
              status: "available",
              health: 96,
              activeEvent: "Available",
              crestron: "mock",
              display: "on",
              screenconnect: true,
              wattbox: false,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Display", "NEC", "Sample", "Sanitized host"]]
            }
          ]
        },
        {
          code: "Obsn",
          name: "Obsidian Hall",
          x: 62,
          y: 38,
          rooms: [
            {
              number: "205",
              type: "Seminar Room",
              status: "in-use",
              health: 88,
              activeEvent: "Seminar until 1:30 PM",
              crestron: "mock",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: ["INC0012102 - Display input verified"] },
              devices: [["Camera", "AVer", "Sample", "Sanitized host"]]
            }
          ]
        },
        {
          code: "CGRC",
          name: "OSU Cascades Graduate and Research Center",
          x: 52,
          y: 68,
          rooms: [
            {
              number: "130",
              type: "Meeting Room",
              status: "available",
              health: 92,
              activeEvent: "Available",
              crestron: "mock",
              display: "standby",
              screenconnect: false,
              wattbox: false,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: [] },
              devices: [["Codec", "Zoom", "Room Appliance", "Sanitized host"]]
            }
          ]
        }
      ]
    },
    {
      id: "hatfield",
      name: "Hatfield Marine",
      subtitle: "Newport campus",
      connectors: { crestron: "mock", live25: "degraded", screenconnect: "ok", wattbox: "mock", servicenow: "ok" },
      buildings: [
        {
          code: "GVMSB",
          name: "Gladys Valley Marine Studies Building",
          x: 46,
          y: 44,
          rooms: [
            {
              number: "Aud",
              type: "Auditorium",
              status: "available",
              health: 94,
              activeEvent: "Available",
              crestron: "mock",
              display: "on",
              screenconnect: true,
              wattbox: true,
              hybrid: true,
              stale: false,
              incidents: { open: [], closed: ["INC0012088 - Microphone checked"] },
              devices: [["Projector", "Panasonic", "Laser", "Sanitized host"]]
            }
          ]
        },
        {
          code: "HMSC",
          name: "Hatfield Marine Science Center",
          x: 65,
          y: 56,
          rooms: [
            {
              number: "204",
              type: "Teaching Lab",
              status: "issue",
              health: 74,
              activeEvent: "Lab until 3:00 PM",
              crestron: "mock",
              display: "unknown",
              screenconnect: false,
              wattbox: true,
              hybrid: false,
              stale: true,
              incidents: { open: ["INC0012411 - Display not reporting"], closed: [] },
              devices: [["Display", "LG", "Sample", "Sanitized host"]]
            }
          ]
        }
      ]
    }
  ],
  filters: [
    { id: "active", label: "Active class/event" },
    { id: "openIncident", label: "Open incident" },
    { id: "offline", label: "Room offline" },
    { id: "issue", label: "Device issue" },
    { id: "wattbox", label: "WattBox-enabled" },
    { id: "screenconnect", label: "ScreenConnect" },
    { id: "hybrid", label: "Hybrid capable" },
    { id: "stale", label: "Stale data" }
  ]
};
