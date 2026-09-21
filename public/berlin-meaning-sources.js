(() => {
  'use strict';

  window.BERLIN_MEANING_SOURCES = {
    weather: {
      id:'weather', label:'Weather now', lens:'now', kind:'modeled', type:'json',
      source:'Open-Meteo', freshness:1, confidence:.84, utility:.82, surprise:.45,
      note:'Modeled current weather at the selected point.'
    },
    air: {
      id:'air', label:'Air now', lens:'now', kind:'modeled', type:'json',
      source:'CAMS via Open-Meteo', freshness:.95, confidence:.76, utility:.78, surprise:.55,
      note:'Modeled PM2.5 and related air context at the selected point.'
    },
    transit: {
      id:'transit', label:'Transit movement', lens:'infrastructure', kind:'live', type:'json',
      source:'VBB realtime radar', freshness:1, confidence:.82, utility:.9, surprise:.52,
      note:'Live vehicles returned in a small box around the selected point.'
    },
    trees: {
      id:'trees', label:'Mapped trees', lens:'nature', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/baumbestand',
      patterns:[/strassenbaeume/i,/anlagenbaeume/i,/baum/i],
      source:'Geoportal Berlin', freshness:.82, confidence:.86, utility:.68, surprise:.52,
      note:'Official mapped tree features nearby; feature count is not canopy quality.'
    },
    green: {
      id:'green', label:'Green space / playgrounds', lens:'life', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/gruenanlagen',
      patterns:[/gruen/i,/anlage/i,/spiel/i],
      source:'Geoportal Berlin', freshness:.92, confidence:.9, utility:.88, surprise:.62,
      note:'Official dedicated public green spaces including public playgrounds.'
    },
    buildingAge: {
      id:'buildingAge', label:'Building age', lens:'history', kind:'historical', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/ua_gebaeudealter',
      patterns:[/gebaeude/i,/alter/i,/bau/i],
      source:'Umweltatlas Berlin', freshness:.38, confidence:.78, utility:.52, surprise:.86,
      note:'Dominant residential building-age class by block; old structural context, not a current building survey.'
    },
    wall: {
      id:'wall', label:'Berlin Wall, 1989', lens:'history', kind:'historical', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/berlinermauer',
      patterns:[/mauer/i,/grenz/i],
      source:'Berlin Open Data / Forum für Geschichte und Gegenwart', freshness:.48, confidence:.92, utility:.46, surprise:.95,
      note:'Digitized 1989 border installations; historical geometry rather than a current feature.'
    },
    heat: {
      id:'heat', label:'Heat / climate analysis', lens:'nature', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/ua_klimaanalyse_2022',
      patterns:[/pet/i,/utci/i,/klima/i,/therm/i,/block/i],
      source:'Umweltatlas Berlin', freshness:.66, confidence:.84, utility:.86, surprise:.68,
      note:'Official planning/climate analysis; not today’s measured temperature.'
    },
    justice: {
      id:'justice', label:'Environmental-justice context', lens:'life', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/ua_umweltgerechtigkeit2023',
      patterns:[/umwelt/i,/gerecht/i,/belast/i,/mehrfach/i],
      source:'Umweltatlas Berlin', freshness:.74, confidence:.84, utility:.86, surprise:.72,
      note:'Integrated official burden context; Deep City does not invent its own morality score.'
    },
    hospitals: {
      id:'hospitals', label:'Hospitals', lens:'infrastructure', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/krankenhaeuser',
      patterns:[/kranken/i,/hospital/i],
      source:'Geoportal Berlin', freshness:.78, confidence:.9, utility:.74, surprise:.34,
      note:'Official hospital locations; proximity is not capacity or access.'
    },
    sports: {
      id:'sports', label:'Public sports facilities', lens:'life', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/sportstandorte',
      patterns:[/sport/i,/standort/i],
      source:'Berlin Open Data', freshness:.8, confidence:.88, utility:.76, surprise:.56,
      note:'Public core sports facilities on state-owned land.'
    },
    bathing: {
      id:'bathing', label:'Bathing-water places', lens:'nature', kind:'structural', type:'wfs',
      endpoint:'https://gdi.berlin.de/services/wfs/badegewaesser',
      patterns:[/bade/i,/gewaesser/i,/probe/i],
      source:'LAGeSo / Geoportal Berlin', freshness:.9, confidence:.9, utility:.8, surprise:.75,
      note:'Official designated bathing-water context and quality-related features.'
    }
  };

  window.BERLIN_MEANING_LENSES = {
    all:{label:'BEST OF'},
    now:{label:'NOW'},
    life:{label:'LIFE'},
    history:{label:'HISTORY'},
    infrastructure:{label:'INFRA'},
    nature:{label:'NATURE'}
  };

  window.BERLIN_MEANING_PERSONAS = {
    visitor:{
      label:'Visiting',
      lensWeights:{now:.85,life:.9,history:1.35,infrastructure:.8,nature:1.1},
      utility:.8,surprise:1.25,freshness:.8
    },
    local:{
      label:'I live here',
      lensWeights:{now:1.2,life:1.15,history:.75,infrastructure:1.2,nature:1.15},
      utility:1.25,surprise:.75,freshness:1.15
    },
    surprise:{
      label:'Surprise me',
      lensWeights:{now:.9,life:1,history:1.3,infrastructure:.8,nature:1.1},
      utility:.7,surprise:1.5,freshness:.85
    }
  };
})();