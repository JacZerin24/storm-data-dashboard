let map;
let eventLayer;
let allCwaBoundaryLayer;
let selectedCwaBoundaryLayer;
let countyBoundaryLayer;
let landZoneBoundaryLayer;
let marineZoneBoundaryLayer;

const boundaryStyles = {
  all_cwas: {
    color: '#4b5563',
    weight: 1,
    opacity: 0.65,
    fillOpacity: 0
  },
  selected_cwa: {
    color: '#111827',
    weight: 3,
    opacity: 1,
    fillOpacity: 0
  },
  counties: {
    color: '#6b7280',
    weight: 1.5,
    opacity: 0.9,
    fillOpacity: 0.02
  },
  land_zones: {
    color: '#2563eb',
    weight: 1.5,
    opacity: 0.9,
    fillOpacity: 0.02
  },
  marine_zones: {
    color: '#0891b2',
    weight: 1.5,
    opacity: 0.9,
    fillOpacity: 0.04
  }
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function initializeMap() {
  if (map) {
    setTimeout(function () {
      map.invalidateSize();
    }, 0);
    return;
  }

  map = L.map('map').setView([30.4, -90.1], 7);

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: 'OpenStreetMap contributors'
  }).addTo(map);

  allCwaBoundaryLayer = L.layerGroup().addTo(map);
  selectedCwaBoundaryLayer = L.layerGroup().addTo(map);
  countyBoundaryLayer = L.layerGroup();
  landZoneBoundaryLayer = L.layerGroup();
  marineZoneBoundaryLayer = L.layerGroup();

  const overlays = {
    'All CWA Boundaries': allCwaBoundaryLayer,
    'Selected WFO CWA': selectedCwaBoundaryLayer,
    'Selected WFO Counties/Parishes': countyBoundaryLayer,
    'Selected WFO Land Zones': landZoneBoundaryLayer,
    'Selected WFO Marine Zones': marineZoneBoundaryLayer
  };

  L.control.layers(null, overlays, {
    collapsed: false
  }).addTo(map);

  eventLayer = L.geoJSON(null, {
    pointToLayer: function (feature, latlng) {
      return L.circleMarker(latlng, {
        radius: 8,
        weight: 2,
        opacity: 1,
        fillOpacity: 0.75
      });
    },
    onEachFeature: function (feature, layer) {
      const properties = feature.properties || {};
      const popupHtml = [
        '<strong>' + escapeHtml(properties.event_type || 'Storm Data Event') + '</strong>',
        escapeHtml(properties.county_or_zone || ''),
        escapeHtml(properties.begin_time_utc || ''),
        escapeHtml((properties.magnitude ?? '') + ' ' + (properties.magnitude_units || '')),
        '<small>' + escapeHtml(properties.event_narrative || '') + '</small>'
      ].join('<br>');

      layer.bindPopup(popupHtml);
    }
  }).addTo(map);

  loadAllCwaBoundaries();

  setTimeout(function () {
    map.invalidateSize();
  }, 100);
}

function getFirstProperty(properties, names) {
  for (const name of names) {
    if (properties[name] !== undefined && properties[name] !== null && properties[name] !== '') {
      return properties[name];
    }
  }
  return '';
}

function buildBoundaryPopup(properties) {
  const name = getFirstProperty(properties, ['NAME', 'name', 'CWA', 'WFO', 'ZONE', 'ID', 'STATE_ZONE', 'STATEZONE', 'COUNTYNAME', 'COUNTY']);
  const state = getFirstProperty(properties, ['STATE', 'state', 'ST']);
  const zone = getFirstProperty(properties, ['ZONE', 'zone', 'STATE_ZONE', 'STATEZONE', 'ID']);
  const wfo = getFirstProperty(properties, ['WFO', 'wfo', 'CWA', 'cwa', 'GL_WFO']);

  const rows = [];

  if (name) {
    rows.push('<strong>' + escapeHtml(name) + '</strong>');
  } else {
    rows.push('<strong>Boundary Feature</strong>');
  }
  if (state) {
    rows.push('State: ' + escapeHtml(state));
  }
  if (zone) {
    rows.push('Zone/ID: ' + escapeHtml(zone));
  }
  if (wfo) {
    rows.push('WFO/CWA: ' + escapeHtml(wfo));
  }

  return rows.join('<br>');
}

function makeBoundaryGeoJsonLayer(geojson, style) {
  return L.geoJSON(geojson, {
    style: style,
    onEachFeature: function (feature, layer) {
      layer.bindPopup(buildBoundaryPopup(feature.properties || {}));
    }
  });
}

async function fetchGeoJson(path) {
  const response = await fetch(path);

  if (!response.ok) {
    return null;
  }

  return response.json();
}

async function loadAllCwaBoundaries() {
  const boundaryStatus = document.getElementById('boundary-status');
  const path = 'data/boundaries/all_cwas.geojson';
  const geojson = await fetchGeoJson(path);

  if (!geojson) {
    if (boundaryStatus) {
      boundaryStatus.textContent = 'All CWA boundaries have not been generated yet. Run the boundary build workflow.';
    }
    return;
  }

  allCwaBoundaryLayer.clearLayers();
  makeBoundaryGeoJsonLayer(geojson, boundaryStyles.all_cwas).addTo(allCwaBoundaryLayer);

  if (boundaryStatus) {
    boundaryStatus.textContent = 'Loaded all CWA boundaries. Select a WFO/month/year to load WFO-specific counties and zones.';
  }
}

async function loadOneWfoBoundaryLayer(path, targetGroup, style) {
  targetGroup.clearLayers();

  const geojson = await fetchGeoJson(path);

  if (!geojson) {
    return false;
  }

  makeBoundaryGeoJsonLayer(geojson, style).addTo(targetGroup);
  return true;
}

async function loadWfoBoundaryLayers(wfo) {
  const boundaryStatus = document.getElementById('boundary-status');
  const basePath = 'data/boundaries/by_wfo/' + wfo;

  selectedCwaBoundaryLayer.clearLayers();
  countyBoundaryLayer.clearLayers();
  landZoneBoundaryLayer.clearLayers();
  marineZoneBoundaryLayer.clearLayers();

  const results = [];

  results.push({
    label: 'selected CWA',
    loaded: await loadOneWfoBoundaryLayer(basePath + '/cwa.geojson', selectedCwaBoundaryLayer, boundaryStyles.selected_cwa)
  });
  results.push({
    label: 'counties/parishes',
    loaded: await loadOneWfoBoundaryLayer(basePath + '/counties_parishes.geojson', countyBoundaryLayer, boundaryStyles.counties)
  });
  results.push({
    label: 'land zones',
    loaded: await loadOneWfoBoundaryLayer(basePath + '/land_zones.geojson', landZoneBoundaryLayer, boundaryStyles.land_zones)
  });
  results.push({
    label: 'marine zones',
    loaded: await loadOneWfoBoundaryLayer(basePath + '/marine_zones.geojson', marineZoneBoundaryLayer, boundaryStyles.marine_zones)
  });

  if (!map.hasLayer(countyBoundaryLayer)) {
    countyBoundaryLayer.addTo(map);
  }
  if (!map.hasLayer(landZoneBoundaryLayer)) {
    landZoneBoundaryLayer.addTo(map);
  }
  if (!map.hasLayer(marineZoneBoundaryLayer)) {
    marineZoneBoundaryLayer.addTo(map);
  }

  const loaded = results.filter(function (item) {
    return item.loaded;
  }).map(function (item) {
    return item.label;
  });

  const missing = results.filter(function (item) {
    return !item.loaded;
  }).map(function (item) {
    return item.label;
  });

  if (boundaryStatus) {
    if (loaded.length > 0) {
      boundaryStatus.textContent = 'Loaded ' + escapeHtml(wfo) + ' boundary layers: ' + loaded.join(', ') + '.';
    } else {
      boundaryStatus.textContent = 'No WFO-specific boundary layers found for ' + escapeHtml(wfo) + '. Run the boundary build workflow.';
    }
  }

  if (missing.length > 0) {
    console.warn('Missing WFO boundary layers for ' + wfo + ':', missing.join(', '));
  }

  setTimeout(function () {
    map.invalidateSize();
  }, 100);
}

async function loadGeoJson(geoJsonPath) {
  initializeMap();
  eventLayer.clearLayers();

  const response = await fetch(geoJsonPath);

  if (!response.ok) {
    throw new Error('GeoJSON file not found: ' + geoJsonPath);
  }

  const geojson = await response.json();
  eventLayer.addData(geojson);

  setTimeout(function () {
    map.invalidateSize();

    const bounds = eventLayer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [30, 30],
        maxZoom: 10
      });
    }
  }, 100);
}

function renderEventTable(events) {
  if (events.length === 0) {
    return '<p>No events found.</p>';
  }

  const rows = events.map(function (event) {
    return '<tr>' +
      '<td>' + escapeHtml(event.begin_time_utc || '') + '</td>' +
      '<td>' + escapeHtml(event.event_type || '') + '</td>' +
      '<td>' + escapeHtml(event.county_or_zone || event.cz_name || '') + '</td>' +
      '<td>' + escapeHtml((event.magnitude ?? '') + ' ' + (event.magnitude_units || '')) + '</td>' +
      '<td>' + escapeHtml(event.event_narrative || '') + '</td>' +
      '</tr>';
  }).join('');

  return '<table>' +
    '<thead>' +
    '<tr>' +
    '<th>Time UTC</th>' +
    '<th>Type</th>' +
    '<th>Location</th>' +
    '<th>Magnitude</th>' +
    '<th>Narrative</th>' +
    '</tr>' +
    '</thead>' +
    '<tbody>' + rows + '</tbody>' +
    '</table>';
}

document.getElementById('load-button').addEventListener('click', async function () {
  const month = document.getElementById('month-select').value;
  const year = document.getElementById('year-input').value;
  const wfo = document.getElementById('wfo-input').value.trim().toUpperCase();

  const statusPanel = document.getElementById('status-panel');
  const summaryPanel = document.getElementById('summary-panel');
  const eventsTable = document.getElementById('events-table');

  const basePath = 'data/stormdata/' + year + '/' + month + '/' + wfo;
  const eventsPath = basePath + '/events.json';
  const geoJsonPath = basePath + '/events.geojson';

  statusPanel.innerHTML = '<h2>Status</h2><p>Loading: ' + escapeHtml(eventsPath) + '</p>';

  try {
    await loadWfoBoundaryLayers(wfo);

    const response = await fetch(eventsPath);

    if (!response.ok) {
      throw new Error('File not found: ' + eventsPath);
    }

    const data = await response.json();
    const events = data.events || [];

    summaryPanel.innerHTML = '<h2>Summary</h2>' +
      '<p><strong>WFO:</strong> ' + escapeHtml(data.metadata.wfo) + '</p>' +
      '<p><strong>Month:</strong> ' + escapeHtml(data.metadata.year + '-' + String(data.metadata.month).padStart(2, '0')) + '</p>' +
      '<p><strong>Total events:</strong> ' + escapeHtml(events.length) + '</p>' +
      '<p><strong>Schema version:</strong> ' + escapeHtml(data.metadata.schema_version) + '</p>';

    eventsTable.innerHTML = renderEventTable(events);

    await loadGeoJson(geoJsonPath);

    statusPanel.innerHTML = '<h2>Status</h2><p>Loaded ' + escapeHtml(events.length) +
      ' event(s), all CWA boundaries, and selected WFO boundary layers for ' + escapeHtml(wfo) + ' ' +
      escapeHtml(year + '-' + month) + '.</p>';
  } catch (error) {
    statusPanel.innerHTML = '<h2>Status</h2><p>' + escapeHtml(error.message) + '</p>' +
      '<p>This usually means that sample data has not been created for that year/month/WFO yet.</p>';

    summaryPanel.innerHTML = '<h2>Summary</h2><p>No data loaded.</p>';
    eventsTable.innerHTML = '<p>No event table available.</p>';
  }
});

window.addEventListener('load', function () {
  initializeMap();
});

window.addEventListener('resize', function () {
  if (map) {
    map.invalidateSize();
  }
});
