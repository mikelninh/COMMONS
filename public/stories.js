window.WORLD_PULSE_STORIES = [
  {
    id: "nepal-flash-floods-2026",
    slug: "nepal-water-returns",
    order: 1,
    country: "Nepal",
    countryId: "524",
    title: "Water Returns",
    subtitle: "Flash floods → response → measurable outcome",
    eventTitle: "Flash Floods 2026",
    status: "OPEN LOOP",
    statusLabel: "Response underway",
    updatedAt: "8 Sep 2026",
    lat: 28.15,
    lon: 85.3,
    colors: {
      attention: "#d2b06d",
      outcome: "#9acb97",
      memory: "#9acb97"
    },
    grammar: ["Pulse", "Thread", "Bloom"],
    timeLabels: [
      "26 Aug · pulse",
      "27 Aug · response",
      "08 Sep · outcome",
      "Now · open loop"
    ],
    semantic: {
      threadStart: 2.3,
      threadEnd: 3.35,
      bloomStart: 4.85,
      bloomEnd: 6.15,
      memoryStart: 7.55,
      memoryEnd: 8.35,
      silenceIndex: 5,
      milestones: [1.7, 4.7, 7.55]
    },
    terrain: {
      caption: "NEPAL · GEOGRAPHIC DESCENT",
      disclosure: "country outline is geographic · relief field is stylized, not elevation data"
    },
    primaryAction: {
      label: "Help through IFRC ↗",
      url: "https://www.ifrc.org/donate"
    },
    evidence: [
      {
        date: "27 Aug 2026",
        label: "IFRC Emergency Appeal",
        url: "https://www.ifrc.org/press-release/ifrc-launches-chf-25-million-emergency-appeal-response-devastating-nepal-flash-floods",
        note: "Early affected-population estimate, appeal amount and named response priorities."
      },
      {
        date: "08 Sep 2026",
        label: "IFRC response update",
        url: "https://www.ifrc.org/press-release/nepal-floods-ifrc-delivers-safe-water-and-health-care-affected-communities",
        note: "Safe drinking water restored for around 2,000 people and mobile primary clinic capacity."
      },
      {
        date: "Responder",
        label: "Nepal Red Cross Society",
        url: "https://www.ifrc.org/national-societies-directory/nepal-red-cross-society",
        note: "Responder identity in the IFRC National Society directory."
      }
    ],
    guardrails: [
      "~93,000 is not presented as a final affected-population count.",
      "We do not claim every affected person has been reached.",
      "We do not show a funding percentage without a current authoritative source.",
      "We do not imply that a particular donation caused the displayed outcomes.",
      "The loop remains open. Newer evidence should extend the timeline instead of rewriting history."
    ],
    share: {
      value: "~2,000",
      label: "people with safe drinking water restored in Nuwakot",
      note: "A documented response outcome. Not a claim that any single contribution caused it.",
      evidenceLine: "Outcome evidence · IFRC · 8 Sep 2026 · Loop open"
    },
    thread: {
      startLat: 27.7172,
      startLng: 85.3240,
      endLat: 27.95,
      endLng: 85.18
    },
    bloom: [
      [27.94,85.13,.64],[27.97,85.17,.52],[27.92,85.20,.46],[28.00,85.10,.38],
      [27.90,85.15,.33],[27.96,85.24,.29],[28.03,85.18,.25],[27.88,85.09,.24],
      [28.01,85.27,.22],[27.86,85.22,.20]
    ],
    scenes: [
      {
        id: "signal", milestone: 0, terrain: 0,
        kicker: "26 Aug 2026 · Pulse",
        composition: "left-monument",
        camera: {lat: 22, lng: 79, altitude: 1.78},
        offset: [245, -8],
        headline: "Flash floods struck <span class='attention'>northern Nepal.</span>",
        copy: "Homes, roads and bridges were damaged and communities were isolated. The first visual state is intentionally simple: a disturbance, not a conclusion.",
        source: "IFRC · 27 Aug 2026", duration: 5200
      },
      {
        id: "impact", milestone: 0, terrain: .08,
        kicker: "Early estimate · Human impact",
        composition: "metric-left",
        camera: {lat: 28.1, lng: 85.3, altitude: 1.28},
        offset: [280, 0],
        value: "~93,000", tone: "attention",
        label: "people may have been affected",
        copy: "An early IFRC estimate while assessments were continuing. It is not presented as a final affected-population count.",
        source: "IFRC Emergency Appeal · 27 Aug 2026", duration: 5700
      },
      {
        id: "descent", milestone: 1, terrain: .58,
        kicker: "27 Aug 2026 · Descent",
        composition: "right-whisper",
        camera: {lat: 27.9, lng: 84.8, altitude: 1.14},
        offset: [-235, -8],
        headline: "Move closer. <span class='human'>The response becomes visible.</span>",
        copy: "The globe gives way to a geographic field of Nepal. The country outline is geographic; the relief treatment is intentionally stylized and is not elevation data.",
        source: "Geographic outline · World Atlas · visual relief treatment · COMMONS", duration: 5200
      },
      {
        id: "verify", milestone: 1, terrain: 1,
        kicker: "Verified response · Thread",
        composition: "right-whisper",
        camera: {lat: 27.9, lng: 84.8, altitude: 1.08},
        offset: [-250, -8],
        headline: "The signal became <span class='human'>a verified response.</span>",
        copy: "IFRC launched a formal Emergency Appeal alongside Nepal Red Cross Society operations. The luminous thread is a semantic response pathway — not a tracked shipment route.",
        source: "Primary evidence · IFRC", duration: 5400
      },
      {
        id: "response", milestone: 1, terrain: 1,
        kicker: "Verified response",
        composition: "center-monument",
        camera: {lat: 27.9, lng: 84.9, altitude: 1.08},
        offset: [0, 70],
        value: "CHF 25M", tone: "attention",
        label: "Emergency Appeal",
        copy: "Shelter, health, clean water, sanitation, cash assistance and recovery were named response priorities.",
        source: "IFRC + Nepal Red Cross Society", duration: 5600
      },
      {
        id: "silence", milestone: 2, terrain: 1,
        kicker: "08 Sep 2026",
        composition: "silence-scene",
        camera: {lat: 28.03, lng: 85.16, altitude: 1.04},
        offset: [0, -20],
        value: "~2,000", tone: "outcome",
        label: "people", copy: "", source: "", silent: true, duration: 6100
      },
      {
        id: "outcome", milestone: 2, terrain: 1,
        kicker: "08 Sep 2026 · Bloom",
        composition: "low-left",
        camera: {lat: 28.03, lng: 85.16, altitude: 1.04},
        offset: [250, -60],
        headline: "<span class='outcome'>Safe drinking water</span> was restored for around 2,000 people in Nuwakot.",
        copy: "This is evidence that the response reached people. It is not proof that any one contribution caused the outcome.",
        source: "IFRC outcome update · 8 Sep 2026", duration: 6500
      },
      {
        id: "capacity", milestone: 2, terrain: .82,
        kicker: "Response capacity",
        composition: "metric-right",
        camera: {lat: 28.03, lng: 85.16, altitude: 1.1},
        offset: [-250, -10],
        value: "100/day", tone: "outcome",
        label: "mobile primary clinic capacity",
        copy: "A concrete piece of response capacity reported in the same IFRC update.",
        source: "IFRC · 8 Sep 2026", duration: 5200
      },
      {
        id: "memory", milestone: 3, terrain: .08,
        kicker: "Memory of Earth",
        composition: "right-whisper",
        camera: {lat: 25.5, lng: 82.5, altitude: 1.64},
        offset: [-220, 15],
        headline: "The planet keeps <span class='outcome'>a memory of response.</span>",
        copy: "This mark represents this documented Nepal response only. Over time, verified actions can leave a truthful visual memory without turning suffering into a leaderboard.",
        source: "COMMONS · one recorded response story", duration: 5400
      },
      {
        id: "you", milestone: 3, terrain: 0,
        kicker: "Now · Open loop",
        composition: "final-center",
        camera: {lat: 18, lng: 74, altitude: 2.05},
        offset: [0, 25],
        headline: "What happens next is <span class='human'>still being written.</span>",
        copy: "Help through the verified response, inspect the evidence, or pass the story on with its provenance intact.",
        source: "Last outcome evidence in this story · 8 Sep 2026",
        duration: 12000, actions: true
      }
    ]
  },

  {
    id: "bhutan-rabies-elimination-2026",
    slug: "bhutan-the-last-transmission",
    order: 2,
    country: "Bhutan",
    countryId: "064",
    title: "The Last Transmission",
    subtitle: "One Health → prevention → elimination",
    eventTitle: "Dog-mediated human rabies elimination",
    status: "ELIMINATION VALIDATED",
    statusLabel: "Elimination achieved",
    updatedAt: "16 Sep 2026",
    lat: 27.5142,
    lon: 90.4336,
    colors: {
      attention: "#8faab7",
      outcome: "#d8d5bd",
      memory: "#a9cdb1"
    },
    grammar: ["Threat", "Network", "Silence"],
    timeLabels: [
      "Then · threat",
      "Years · One Health",
      "Jun 2023 · zero deaths",
      "04 Sep · validated"
    ],
    semantic: {
      threadStart: 2.15,
      threadEnd: 3.45,
      bloomStart: 4.7,
      bloomEnd: 6.0,
      memoryStart: 7.3,
      memoryEnd: 8.15,
      silenceIndex: 5,
      milestones: [1.7, 4.55, 7.25]
    },
    terrain: {
      caption: "BHUTAN · GEOGRAPHIC DESCENT",
      disclosure: "country outline is geographic · internal relief is stylized, not elevation data"
    },
    primaryAction: {
      label: "Read WHO validation ↗",
      url: "https://www.who.int/news/item/04-09-2026-who-validates-bhutan-for-eliminating-dog-transmitted-human-rabies"
    },
    evidence: [
      {
        date: "04 Sep 2026",
        label: "WHO validation",
        url: "https://www.who.int/news/item/04-09-2026-who-validates-bhutan-for-eliminating-dog-transmitted-human-rabies",
        note: "WHO validated Bhutan’s elimination of dog-transmitted human rabies as a public health problem."
      },
      {
        date: "16 Sep 2026",
        label: "WHO feature",
        url: "https://www.who.int/news-room/feature-stories/detail/bhutan-shows-the-region-rabies-elimination-is-possible",
        note: "Zero human deaths from dog-mediated rabies since June 2023; describes the sustained One Health programme."
      }
    ],
    guardrails: [
      "WHO validation is elimination as a public health problem, not a claim that rabies can never reappear.",
      "Zero refers to human deaths from dog-mediated rabies since June 2023, not zero dog bites or zero animal rabies risk.",
      "The visual network is semantic and does not depict literal vaccination routes.",
      "Bhutan continues PEP access, dog vaccination, population management and surveillance to sustain the achievement."
    ],
    share: {
      value: "0",
      label: "human deaths from dog-mediated rabies since June 2023",
      note: "WHO validated elimination as a public health problem on 4 Sep 2026.",
      evidenceLine: "WHO validation · 4 Sep 2026 · elimination must be sustained"
    },
    thread: {
      startLat: 27.4728,
      startLng: 89.6390,
      endLat: 26.86,
      endLng: 91.15
    },
    bloom: [
      [27.48,89.63,.40],[27.35,90.10,.36],[27.28,90.65,.34],[27.18,91.05,.30],
      [26.95,90.70,.28],[26.92,89.95,.25],[27.58,90.75,.24]
    ],
    scenes: [
      {
        id: "signal", milestone: 0, terrain: 0,
        kicker: "Before elimination · Threat",
        composition: "left-monument",
        camera: {lat: 23, lng: 85, altitude: 1.85},
        offset: [245, -8],
        headline: "Rabies used to remain a <span class='attention'>real human threat</span> in Bhutan.",
        copy: "Dog-mediated rabies was especially concerning in southern border districts. The story here is not one outbreak — it is years of prevention.",
        source: "WHO Bhutan · 1 Sep 2026", duration: 5200
      },
      {
        id: "stakes", milestone: 0, terrain: .08,
        kicker: "Why prevention matters",
        composition: "metric-left",
        camera: {lat: 27.5, lng: 90.4, altitude: 1.30},
        offset: [280, 0],
        value: "99%", tone: "attention",
        label: "of human rabies transmission globally is linked to infected dogs",
        copy: "WHO notes that rabies is almost always fatal once clinical symptoms appear, while human deaths are preventable.",
        source: "WHO · rabies validation note", duration: 5600
      },
      {
        id: "descent", milestone: 1, terrain: .62,
        kicker: "Years of work · Descent",
        composition: "right-whisper",
        camera: {lat: 27.5, lng: 90.4, altitude: 1.14},
        offset: [-230, -5],
        headline: "The answer was not one intervention. <span class='human'>It was a system.</span>",
        copy: "Human and animal health authorities worked together through surveillance, rapid response, post-exposure prophylaxis, dog vaccination and dog population management.",
        source: "WHO · One Health approach", duration: 5400
      },
      {
        id: "network", milestone: 1, terrain: 1,
        kicker: "One Health · Network",
        composition: "right-whisper",
        camera: {lat: 27.45, lng: 90.3, altitude: 1.06},
        offset: [-245, -8],
        headline: "Health workers. Veterinary teams. Volunteers. <span class='human'>One network.</span>",
        copy: "WHO credits national leadership, health and veterinary professionals, De-suung volunteers and communities with sustaining the programme across the country.",
        source: "WHO validation · 4 Sep 2026", duration: 5600
      },
      {
        id: "sustain", milestone: 1, terrain: 1,
        kicker: "Prevention at scale",
        composition: "center-monument",
        camera: {lat: 27.45, lng: 90.4, altitude: 1.08},
        offset: [0, 65],
        value: "20", tone: "attention",
        label: "districts with continued free access to post-exposure prophylaxis",
        copy: "Bhutan says universal free PEP will continue across all 20 Dzongkhags, alongside vaccination and surveillance.",
        source: "WHO · 4 Sep 2026", duration: 5600
      },
      {
        id: "silence", milestone: 2, terrain: 1,
        kicker: "Since June 2023",
        composition: "silence-scene",
        camera: {lat: 27.45, lng: 90.4, altitude: 1.04},
        offset: [0, -20],
        value: "0", tone: "outcome",
        label: "human deaths", copy: "", source: "", silent: true, duration: 6500
      },
      {
        id: "outcome", milestone: 2, terrain: 1,
        kicker: "04 Sep 2026 · Silence",
        composition: "low-left",
        camera: {lat: 27.45, lng: 90.4, altitude: 1.04},
        offset: [250, -60],
        headline: "WHO validated Bhutan’s <span class='outcome'>elimination of dog-transmitted human rabies</span> as a public health problem.",
        copy: "The most powerful visual here is absence: a threat that has stopped taking human lives, while the systems that keep it away remain active.",
        source: "WHO validation · 4 Sep 2026", duration: 6500
      },
      {
        id: "sustain-next", milestone: 2, terrain: .82,
        kicker: "Elimination is maintenance",
        composition: "metric-right",
        camera: {lat: 27.45, lng: 90.4, altitude: 1.12},
        offset: [-250, -10],
        value: "2030", tone: "outcome",
        label: "global Zero by 30 target",
        copy: "Bhutan’s achievement is one country-level milestone inside the global goal of ending human deaths from dog-mediated rabies.",
        source: "WHO / WOAH / FAO · Zero by 30", duration: 5200
      },
      {
        id: "memory", milestone: 3, terrain: .08,
        kicker: "Memory of Earth",
        composition: "right-whisper",
        camera: {lat: 25.5, lng: 88.5, altitude: 1.66},
        offset: [-220, 15],
        headline: "Earth can remember <span class='outcome'>what stopped happening.</span>",
        copy: "This mark records a validated public-health elimination — while keeping the continuing work required to sustain it visible.",
        source: "COMMONS · WHO-validated elimination", duration: 5400
      },
      {
        id: "you", milestone: 3, terrain: 0,
        kicker: "Validated · must be sustained",
        composition: "final-center",
        camera: {lat: 20, lng: 84, altitude: 2.04},
        offset: [0, 25],
        headline: "Sometimes progress looks like <span class='human'>silence.</span>",
        copy: "Read the validation, inspect how the One Health system worked, or continue to the next story.",
        source: "WHO · evidence current through Sep 2026",
        duration: 12000, actions: true
      }
    ]
  },

  {
    id: "drc-ebola-bundibugyo-2026",
    slug: "drc-outrunning-an-epidemic",
    order: 3,
    country: "DRC",
    countryId: "180",
    title: "Outrunning an Epidemic",
    subtitle: "Spread → response → open loop",
    eventTitle: "Bundibugyo Ebola outbreak 2026",
    status: "OPEN LOOP",
    statusLabel: "Response racing the outbreak",
    updatedAt: "16 Sep 2026",
    lat: 1.8,
    lon: 28.5,
    colors: {
      attention: "#be8179",
      outcome: "#d2b06d",
      memory: "#d2b06d"
    },
    grammar: ["Spread", "Response", "Open loop"],
    timeLabels: [
      "May · outbreak",
      "Sep · response",
      "16 Sep · mixed signals",
      "Now · open loop"
    ],
    semantic: {
      threadStart: 2.2,
      threadEnd: 3.5,
      bloomStart: 5.4,
      bloomEnd: 6.4,
      memoryStart: 7.4,
      memoryEnd: 8.2,
      silenceIndex: 5,
      milestones: [1.7, 4.6, 7.35]
    },
    terrain: {
      caption: "DRC · GEOGRAPHIC DESCENT",
      disclosure: "country outline is geographic · internal relief is stylized, not outbreak-intensity data"
    },
    primaryAction: {
      label: "Open WHO outbreak hub ↗",
      url: "https://www.who.int/emergencies/situations/ebola-outbreak---drc-2026"
    },
    evidence: [
      {
        date: "16 Sep 2026",
        label: "WHO Alert and Response",
        url: "https://www.who.int/emergencies/alert-and-response",
        note: "DRC: 7,475 confirmed cases, 3,605 confirmed deaths and 1,798 recovered; figures are subject to retrospective revision."
      },
      {
        date: "16 Sep 2026",
        label: "WHO Director-General briefing",
        url: "https://www.who.int/news-room/speeches/item/who-director-general-s-opening-remarks-at-the-media-briefing-16-september-2026",
        note: "Encouraging signs in some areas, but the epidemic continues to grow and key indicators are not yet improving as needed."
      },
      {
        date: "10 Sep 2026",
        label: "WHO Disease Outbreak News",
        url: "https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON617",
        note: "Detailed outbreak context, geographic expansion and challenges in early detection and care."
      }
    ],
    guardrails: [
      "The case and death counts are time-stamped and may be revised retrospectively.",
      "Recoveries are real response evidence but do not mean the epidemic is improving overall.",
      "WHO reported encouraging signs in some locations while also stating that the epidemic continues to grow.",
      "The visual response thread is semantic and does not depict literal patient, vaccine or supply movements.",
      "No green resolution Bloom is shown: this story remains an open loop."
    ],
    share: {
      value: "7,475",
      label: "confirmed cases in DRC as of 16 Sep 2026",
      note: "WHO reports mixed signals: response gains in some areas, continued growth nationally.",
      evidenceLine: "WHO · data as of 16 Sep 2026 · open loop"
    },
    thread: {
      startLat: -4.325,
      startLng: 15.322,
      endLat: 1.8,
      endLng: 28.5
    },
    bloom: [],
    scenes: [
      {
        id: "signal", milestone: 0, terrain: 0,
        kicker: "May 2026 · Spread",
        composition: "left-monument",
        camera: {lat: -2, lng: 23, altitude: 1.82},
        offset: [245, -8],
        headline: "A Bundibugyo Ebola outbreak began spreading through the <span class='attention'>Democratic Republic of the Congo.</span>",
        copy: "WHO says the outbreak is unfolding in an exceptionally difficult context of distance, mobility, insecurity and strained humanitarian access.",
        source: "WHO outbreak hub · 2026", duration: 5400
      },
      {
        id: "impact", milestone: 0, terrain: .08,
        kicker: "Data as of 16 Sep 2026",
        composition: "metric-left",
        camera: {lat: 1.8, lng: 28.5, altitude: 1.28},
        offset: [280, 0],
        value: "7,475", tone: "attention",
        label: "confirmed cases in DRC",
        copy: "WHO’s emergency table notes that the figures may be revised retrospectively as surveillance data are updated.",
        source: "WHO Alert and Response · 16 Sep 2026", duration: 6000
      },
      {
        id: "descent", milestone: 1, terrain: .60,
        kicker: "A country-sized response problem",
        composition: "right-whisper",
        camera: {lat: 0.8, lng: 27.5, altitude: 1.15},
        offset: [-235, -8],
        headline: "There is not one epidemic here. <span class='human'>There are many local battles.</span>",
        copy: "WHO describes major cities, remote villages, conflict-affected areas, mining zones and highly mobile border regions — all demanding different response conditions.",
        source: "WHO Director-General · 16 Sep 2026", duration: 5600
      },
      {
        id: "response", milestone: 1, terrain: 1,
        kicker: "Response · Thread",
        composition: "right-whisper",
        camera: {lat: 1.5, lng: 28.4, altitude: 1.08},
        offset: [-250, -8],
        headline: "Thousands of responders are trying to <span class='human'>close the distance.</span>",
        copy: "WHO cites the DRC government, Africa CDC, hundreds of partners and thousands of frontline health workers, alongside surveillance, contact tracing, clinical care and research.",
        source: "WHO · 16 Sep 2026", duration: 5700
      },
      {
        id: "deaths", milestone: 1, terrain: 1,
        kicker: "The cost remains severe",
        composition: "center-monument",
        camera: {lat: 1.5, lng: 28.4, altitude: 1.08},
        offset: [0, 70],
        value: "3,605", tone: "attention",
        label: "confirmed deaths in DRC",
        copy: "This is why the story cannot be narrated as a victory. The response and the epidemic are moving at the same time.",
        source: "WHO Alert and Response · 16 Sep 2026", duration: 6000
      },
      {
        id: "silence", milestone: 2, terrain: 1,
        kicker: "Mixed signal",
        composition: "silence-scene",
        camera: {lat: 1.5, lng: 28.4, altitude: 1.05},
        offset: [0, -20],
        value: "1,798", tone: "outcome",
        label: "recovered in DRC", copy: "", source: "", silent: true, duration: 6200
      },
      {
        id: "mixed", milestone: 2, terrain: 1,
        kicker: "16 Sep 2026 · No false Bloom",
        composition: "low-left",
        camera: {lat: 1.5, lng: 28.4, altitude: 1.05},
        offset: [250, -60],
        headline: "There are <span class='outcome'>encouraging signs</span> — and the epidemic is still growing.",
        copy: "WHO reported falling transmission in parts of Ituri and no new South Kivu cases since May, while warning of continued national growth and rapidly rising cases in North Kivu.",
        source: "WHO Director-General · 16 Sep 2026", duration: 6800
      },
      {
        id: "science", milestone: 2, terrain: .78,
        kicker: "Research while responding",
        composition: "metric-right",
        camera: {lat: 1.2, lng: 28.1, altitude: 1.12},
        offset: [-250, -10],
        value: "OPEN", tone: "attention",
        label: "treatment, prophylaxis and vaccine research loop",
        copy: "WHO says treatment and post-exposure prophylaxis trials are accelerating, with vaccine trials expected to begin in the coming weeks.",
        source: "WHO · 16 Sep 2026", duration: 5400
      },
      {
        id: "memory", milestone: 3, terrain: .08,
        kicker: "Memory of Earth · Open",
        composition: "right-whisper",
        camera: {lat: -1, lng: 25, altitude: 1.70},
        offset: [-220, 15],
        headline: "Earth should remember <span class='attention'>unfinished work</span> too.",
        copy: "This mark records a documented response in progress. It is amber, not green: memory does not imply resolution.",
        source: "COMMONS · open-loop response record", duration: 5400
      },
      {
        id: "you", milestone: 3, terrain: 0,
        kicker: "Now · Open loop",
        composition: "final-center",
        camera: {lat: -2, lng: 23, altitude: 2.10},
        offset: [0, 25],
        headline: "The race is <span class='human'>still running.</span>",
        copy: "Inspect the latest WHO evidence, follow the response, or continue to another story of human action.",
        source: "WHO · evidence current through 16 Sep 2026",
        duration: 12000, actions: true
      }
    ]
  }
];
