let map;
let eventLayer;

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
    return;
  }

  map = L.map('map').setView([30.4, -90.1], 7);

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: 'OpenStreetMap contributors'
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

  const bounds = eventLayer.getBounds();

  if (bounds.isValid()) {
    map.fitBounds(bounds, {
      padding: [30, 30],
      maxZoom: 10
    });
  }
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

initializeMap();
