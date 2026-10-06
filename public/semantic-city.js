(function () {
  'use strict';

  var sources = {
    heat: ['STRUCTURAL', 'Umweltatlas Berlin - Heat / climate analysis', "Planning analysis, not today's measured temperature."],
    justice: ['STRUCTURAL', 'Umweltatlas Berlin - Environmental justice', 'Official burden context; no invented morality score.'],
    green: ['STRUCTURAL', 'Geoportal Berlin - Green spaces', 'Mapped green is not identical to shade or cooling quality.'],
    hospitals: ['STRUCTURAL', 'Geoportal Berlin - Hospitals', 'Proximity is not capacity or guaranteed access.'],
    weather: ['MODELED', 'Open-Meteo - Weather model', 'Model output, not an on-site sensor reading.'],
    transit: ['LIVE', 'VBB - Transit movement', 'Movement availability does not guarantee capacity.']
  };

  var scenarios = {
    heat: {
      title: 'Heat resilience',
      question: 'Who should receive attention first during a severe heat event, and why?',
      decision: 'Review Demo Cell A first',
      authority: 'HUMAN DECISION REQUIRED',
      recommendation: 'Heat exposure, social burden, limited green access and a modeled high-temperature forecast converge on the same demo area. The graph recommends attention - not an automatic resource allocation.',
      gate: 'Opening cooling spaces, allocating staff or prioritising districts remains a municipal decision.',
      why: [['Heat risk','structural evidence','0.86'],['Social burden','structural evidence','0.72'],['Green access','structural evidence','0.31'],['Forecast max','modeled evidence','34degC']],
      evidence: ['heat','justice','green','weather'],
      query: 'PREFIX city: <https://commons.local/semantic-city/>\nSELECT ?area ?heat ?burden ?green ?temp WHERE {\n  ?o1 city:about ?area ; city:metric "heatRisk" ; city:value ?heat .\n  ?o2 city:about ?area ; city:metric "socialBurden" ; city:value ?burden .\n  ?o3 city:about ?area ; city:metric "greenAccess" ; city:value ?green .\n  ?o4 city:about ?area ; city:metric "forecastMaxTemp" ; city:value ?temp .\n  FILTER(?heat >= 0.70)\n}\nORDER BY DESC(?heat)',
      nodes: [['area','Demo Cell A','AREA',440,230,'entity'],['heat','Heat risk','0.86',190,100,'fact'],['burden','Social burden','0.72',175,265,'fact'],['green','Green access','0.31',270,420,'fact'],['temp','Forecast','34degC',650,100,'fact'],['people','Sensitive residents','COHORT',690,290,'entity'],['rule','Human review','RULE',610,430,'rule'],['human','Municipal authority','DECIDES',815,405,'human']],
      edges: [['heat','area','about'],['burden','area','about'],['green','area','about'],['temp','area','about'],['people','area','lives in'],['area','rule','supports'],['rule','human','requires approval','hot']]
    },
    resilience: {
      title: 'Critical infrastructure cascade',
      question: 'What could be affected if a critical infrastructure asset fails?',
      decision: 'Expose the cascade, do not execute it',
      authority: 'NEVER AUTO-EXECUTE',
      recommendation: 'A dependency path links one synthetic power asset to traffic signals, transit and hospital access. The useful AI action is to surface the chain and uncertainty for an operator - not to reroute systems autonomously.',
      gate: 'Traffic, energy, transit and emergency-service interventions require current verification and accountable operators.',
      why: [['Substation','synthetic asset','root'],['Traffic signal','depends on substation','1 hop'],['Bus route','depends on signal','2 hops'],['Hospital access','depends on route','3 hops']],
      evidence: ['transit','hospitals'],
      query: 'PREFIX city: <https://commons.local/semantic-city/>\nSELECT ?dependent ?label WHERE {\n  ?dependent city:dependsOn+ <https://commons.local/semantic-city/asset/substation-demo-17> ;\n             <http://www.w3.org/2000/01/rdf-schema#label> ?label .\n}\nORDER BY ?label',
      nodes: [['sub','Substation 17','SYNTHETIC',120,260,'entity'],['sig','Traffic signal','DEPENDS ON',320,140,'entity'],['int','Intersection 42','DEPENDS ON',320,365,'entity'],['bus','Bus route link','TRANSIT',525,140,'entity'],['hospital','Hospital access','CARE',720,140,'entity'],['rule','Operator verification','RULE',610,360,'rule'],['human','Accountable operator','DECIDES',815,360,'human']],
      edges: [['sub','sig','supplies','hot'],['sub','int','supports'],['sig','bus','affects','hot'],['bus','hospital','affects','hot'],['hospital','rule','escalates'],['rule','human','requires','hot']]
    },
    energy: {
      title: 'Energy transition prioritisation',
      question: 'Which renovation candidates deserve deeper assessment under a constrained budget?',
      decision: 'Shortlist, then deliberate',
      authority: 'HUMAN DECISION REQUIRED',
      recommendation: 'The graph can rank evidence such as avoidable CO2 per EURm, but it refuses to hide social priority, feasibility and political weights inside one magic score.',
      gate: 'Budget allocation is a value-laden public decision. AI may structure evidence and trade-offs; humans choose the weights.',
      why: [['Building B','CO2 / cost','56 t / EUR1m'],['Building A','CO2 / cost','82 t / EUR1.8m'],['Building C','social priority','0.81'],['Weights','explicit policy choice','human']],
      evidence: ['justice','heat'],
      query: 'PREFIX city: <https://commons.local/semantic-city/>\nSELECT ?building ?co2 ?cost ?social ((?co2 / ?cost) AS ?co2PerMillion) WHERE {\n  ?o1 city:about ?building ; city:metric "avoidableCO2" ; city:value ?co2 .\n  ?o2 city:about ?building ; city:metric "renovationCost" ; city:value ?cost .\n  ?o3 city:about ?building ; city:metric "socialPriority" ; city:value ?social .\n}\nORDER BY DESC(?co2PerMillion)',
      nodes: [['budget','EUR10m budget','CONSTRAINT',130,260,'rule'],['a','Building A','82t - EUR1.8m',350,100,'entity'],['b','Building B','56t - EUR1.0m',350,260,'entity'],['c','Building C','91t - EUR2.4m',350,420,'entity'],['trade','Trade-off model','NO MAGIC SCORE',610,260,'rule'],['human','Municipal authority','DECIDES',815,260,'human']],
      edges: [['budget','a','constrains'],['budget','b','constrains'],['budget','c','constrains'],['a','trade','evidence'],['b','trade','evidence'],['c','trade','evidence'],['trade','human','options','hot']]
    },
    flood: {
      title: 'Heavy-rain / flood attention routing',
      question: 'What needs attention first before a forecast heavy-rain event?',
      decision: 'Escalate the exposed service chain',
      authority: 'NEVER AUTO-EXECUTE',
      recommendation: 'Modeled exposure is linked through a synthetic road dependency to an emergency route and care facility. The system can raise attention early while keeping forecast uncertainty separate from operational commands.',
      gate: 'Closure, evacuation, dispatch and emergency routing require verified current conditions and accountable authorities.',
      why: [['Road exposure','modeled','0.79'],['Emergency route','depends on road','linked'],['Care facility','depends on route','criticality 0.93'],['Forecast','uncertain by design','verify']],
      evidence: ['weather','hospitals'],
      query: 'PREFIX city: <https://commons.local/semantic-city/>\nSELECT ?service ?criticality WHERE {\n  ?flood city:about ?road ; city:metric "floodExposure" ; city:value ?exposure .\n  ?route city:dependsOn ?road .\n  ?service city:dependsOn ?route .\n  ?critical city:about ?service ; city:metric "serviceCriticality" ; city:value ?criticality .\n  FILTER(?exposure >= 0.70)\n}\nORDER BY DESC(?criticality)',
      nodes: [['forecast','Heavy-rain model','MODELED',130,110,'fact'],['road','Road segment','EXPOSURE .79',330,240,'entity'],['route','Emergency route','DEPENDS ON',530,240,'entity'],['care','Care facility','CRITICAL .93',730,130,'entity'],['rule','Verify + escalate','RULE',650,390,'rule'],['human','Emergency authority','DECIDES',835,390,'human']],
      edges: [['forecast','road','exposes','hot'],['road','route','supports','hot'],['route','care','access','hot'],['care','rule','critical service'],['forecast','rule','uncertain'],['rule','human','requires','hot']]
    }
  };

  var modelTerms = ['PLACE','POPULATION','ASSET','SERVICE','OBSERVATION','SOURCE','RULE','RESPONSIBILITY','ACTION','RECOMMENDATION','UNCERTAINTY','OUTCOME'];
  var current = 'heat';
  var tab = 'evidence';

  function byId(id) {
    return document.getElementById(id);
  }

  function nodeById(s, id) {
    return s.nodes.find(function (node) {
      return node[0] === id;
    });
  }

  function esc(value) {
    return String(value).replace(/[&<>]/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];
    });
  }

  function renderGraph(s) {
    var svg = byId('graphSvg');
    var ns = 'http://www.w3.org/2000/svg';
    svg.innerHTML = '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#3b544a"/></marker><marker id="arrowHot" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#bcff65"/></marker></defs>';

    s.edges.forEach(function (edge) {
      var a = nodeById(s, edge[0]);
      var b = nodeById(s, edge[1]);
      var hot = edge[3];
      if (!a || !b) return;

      var line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', a[3]);
      line.setAttribute('y1', a[4]);
      line.setAttribute('x2', b[3]);
      line.setAttribute('y2', b[4]);
      line.setAttribute('class', 'edge' + (hot ? ' hot' : ''));
      line.setAttribute('marker-end', hot ? 'url(#arrowHot)' : 'url(#arrow)');
      svg.appendChild(line);

      var label = document.createElementNS(ns, 'text');
      label.textContent = edge[2];
      label.setAttribute('x', (a[3] + b[3]) / 2);
      label.setAttribute('y', (a[4] + b[4]) / 2 - 7);
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('class', 'edge-label');
      svg.appendChild(label);
    });

    s.nodes.forEach(function (node) {
      var g = document.createElementNS(ns, 'g');
      g.setAttribute('class', 'node ' + node[5]);

      var circle = document.createElementNS(ns, 'circle');
      circle.setAttribute('cx', node[3]);
      circle.setAttribute('cy', node[4]);
      circle.setAttribute('r', 32);
      g.appendChild(circle);

      var title = document.createElementNS(ns, 'text');
      title.setAttribute('x', node[3]);
      title.setAttribute('y', node[4] - 2);
      title.setAttribute('text-anchor', 'middle');
      title.textContent = node[1];
      g.appendChild(title);

      var sub = document.createElementNS(ns, 'text');
      sub.setAttribute('x', node[3]);
      sub.setAttribute('y', node[4] + 13);
      sub.setAttribute('text-anchor', 'middle');
      sub.setAttribute('class', 'sub');
      sub.textContent = node[2];
      g.appendChild(sub);
      svg.appendChild(g);
    });
  }

  function renderWhy(s) {
    byId('whyRows').innerHTML = s.why.map(function (row) {
      return '<div class="why-row"><i></i><div><b>' +
        esc(row[0]) + '</b><p>' + esc(row[1]) +
        '</p></div><em>' + esc(row[2]) + '</em></div>';
    }).join('');
  }

  function renderDrawer() {
    var s = scenarios[current];
    var body = byId('drawerBody');

    document.querySelectorAll('[data-tab]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.tab === tab);
    });

    if (tab === 'query') {
      body.innerHTML = '<pre class="code">' + esc(s.query) + '</pre>';
      return;
    }

    if (tab === 'model') {
      body.innerHTML = '<div class="model-grid">' +
        modelTerms.map(function (term) {
          return '<div>' + term + '</div>';
        }).join('') +
        '</div>';
      return;
    }

    body.innerHTML = '<div class="source-grid">' +
      s.evidence.map(function (id) {
        var source = sources[id];
        return '<article class="source-card"><span>' +
          esc(source[0]) + '</span><b>' +
          esc(source[1]) + '</b><small>' +
          esc(source[2]) + '</small></article>';
      }).join('') +
      '</div>';
  }

  function render(id) {
    current = id;
    var s = scenarios[id];

    document.querySelectorAll('.scenario').forEach(function (button) {
      button.classList.toggle('active', button.dataset.scenario === id);
    });

    byId('graphTitle').textContent = s.title;
    byId('question').textContent = s.question;
    byId('decisionTitle').textContent = s.decision;
    byId('recommendation').textContent = s.recommendation;
    byId('authority').textContent = s.authority;
    byId('gateCopy').textContent = s.gate;
    renderWhy(s);
    renderGraph(s);
    renderDrawer();
  }

  function openDrawer(nextTab) {
    tab = nextTab || tab;
    byId('drawer').classList.add('open');
    renderDrawer();
    byId('drawer').scrollIntoView({
      behavior: 'smooth',
      block: 'nearest'
    });
  }

  document.querySelectorAll('.scenario').forEach(function (button) {
    button.addEventListener('click', function () {
      render(button.dataset.scenario);
    });
  });

  document.querySelectorAll('[data-tab]').forEach(function (button) {
    button.addEventListener('click', function () {
      tab = button.dataset.tab;
      renderDrawer();
    });
  });

  byId('showQuery').addEventListener('click', function () {
    openDrawer('query');
  });

  byId('explainButton').addEventListener('click', function () {
    openDrawer('evidence');
  });

  byId('drawerClose').addEventListener('click', function () {
    byId('drawer').classList.remove('open');
  });

  render(current);
}());
