let map;
let eventLayer;
let boundaryLayerControl;
let cwaBoundaryLayer;
let countyBoundaryLayer;
let landZoneBoundaryLayer;
let marineZoneBoundaryLayer;

const boundaryLayersConfig = [
  {
    key: 'cwa',
    label: 'CWA Boundary',
    path: 'data/boundaries/LIX/cwa.geojson',
    alwaysOn: true,
    style: {
      color: '#111827',
      weight: 3,
      opacity: 1,
      fillOpacity: 0
    }
  },
  {
    key: 'counties',
    label: 'Counties/Parishes',
    path: 'data/boundaries/LIX/counties_parishes.geojson',
    alwaysOn: false,
    style: {
      color: '#6b7280',
      weight: 1.5,
      opacity: 0.9,
      fillOpacity: 0.02
    }
  },
  {
    key: 'land_zones',
    label: 'Land Zones',
    path: 'data/boundaries/LIX/land_zones.geojson',
    alwaysOn: false,
    style: {
      color: '#2563eb',
      weight: 1.5,
      opacity: 0.9,
      fillOpacity: 0.02
    }
  },
  {
    key: 'marine_zones',
    label: 'Marine Zones',
    path: 'data/boundaries/LIX/marine_zones.geojson',
    alwaysOn: false,
    style: {
      color: '#0891b2',
      weight: 1.5,
      opacity: 0.9,
      fillOpacity: 0.04
    }
  }
];

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

  cwaBoundaryLayer = L.layerGroup().addTo(map);
  countyBoundaryLayer = L.layerGroup();
  landZoneBoundaryLayer = L.layerGroup();
  marineZoneBoundaryLayer = L.layerGroup();

  const overlays = {
    'CWA Boundary': cwaBoundaryLayer,
    'Counties/Parishes': countyBoundaryLayer,
    'Land Zones': landZoneBoundaryLayer,
    'Marine Zones': marineZoneBoundaryLayer
  };

  boundaryLayerControl = L.control.layers(null, overlays, {
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

  loadBoundaryLayers();

  setTimeout(function () {
    map.invalidateSize();
  }, 100);
}

function getBoundaryGroup(key) {
  if (key === 'cwa') {
    return cwaBoundaryLayer;
  }
  if (key === 'counties') {
    return countyBoundaryLayer;
  }
  if (key === 'land_zones') {
    return landZoneBoundaryLayer;
  }
  if (key === 'marine_zones') {
    return marineZoneBoundaryLayer;
  }
  return null;
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
  const name = getFirstProperty(properties, ['NAME', 'name', 'CWA', 'WFO', 'ZONE', 'ID', 'STATE_ZONE', 'STATEZONE', 'COUNTYNAME']);
  const state = getFirstProperty(properties, ['STATE', 'state']);
  const zone = getFirstProperty(properties, ['ZONE', 'zone', 'STATE_ZONE', 'STATEZONE']);
  const wfo = getFirstProperty(properties, ['WFO', 'wfo', 'CWA', 'cwa']);

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
    rows.push('Zone: ' + escapeHtml(zone));
  }
  if (wfo) {
    rows.push('WFO/CWA: ' + escapeHtml(wfo));
  }

  return rows.join('<br>');
}

async function loadOneBoundaryLayer(config) {
  const group = getBoundaryGroup(config.key);

  if (!group) {
    return false;
  }

  const response = await fetch(config.path);

  if (!response.ok) {
    return false;
  }

  const geojson = await response.json();

  const layer = L.geoJSON(geojson, {
    style: config.style,
    onEachFeature: function (feature, layer) {
      layer.bindPopup(buildBoundaryPopup(feature.properties || {}));
    }
  });

  layer.addTo(group);

  return true;
}

async function loadBoundaryLayers() {
  const boundaryStatus = document.getElementById('boundary-status');
  const loadedLabels = [];
  const missingLabels = [];

  for (const config of boundaryLayersConfig) {
    try {
      const loaded = await loadOneBoundaryLayer(config);
      if (loaded) {
        loadedLabels.push(config.label);
      } else {
        missingLabels.push(config.label);
      }
    } catch (error) {
      missingLabels.push(config.label);
    }
  }

  if (boundaryStatus) {
    if (loadedLabels.length > 0) {
      boundaryStatus.textContent = 'Loaded boundary layers: ' + loadedLabels.join(', ') + '.';
    } else {
      boundaryStatus.textContent = 'Boundary layers have not been generated yet. Run the boundary build workflow or script.';
    }
  }

  if (missingLabels.length > 0) {
    console.warn('Missing boundary layers:', missingLabels.join(', '));
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
      ' event(s) and mapped available GeoJSON features for ' + escapeHtml(wfo) + ' ' +
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
