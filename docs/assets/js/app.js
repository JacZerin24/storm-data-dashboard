let map;
let eventLayer;
let warningLayer;
let allCwaBoundaryLayer;
let selectedCwaBoundaryLayer;
let countyBoundaryLayer;
let landZoneBoundaryLayer;
let marineZoneBoundaryLayer;

const boundaryStyles = {
  all_cwas: { color: '#4b5563', weight: 1, opacity: 0.65, fillOpacity: 0 },
  selected_cwa: { color: '#111827', weight: 3, opacity: 1, fillOpacity: 0 },
  counties: { color: '#6b7280', weight: 1.5, opacity: 0.9, fillOpacity: 0.02 },
  land_zones: { color: '#2563eb', weight: 1.5, opacity: 0.9, fillOpacity: 0.02 },
  marine_zones: { color: '#0891b2', weight: 1.5, opacity: 0.9, fillOpacity: 0.04 }
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
    setTimeout(function () { map.invalidateSize(); }, 0);
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
  warningLayer = L.layerGroup();

  const overlays = {
    'All CWA Boundaries': allCwaBoundaryLayer,
    'Selected WFO CWA': selectedCwaBoundaryLayer,
    'Selected WFO Counties/Parishes': countyBoundaryLayer,
    'Selected WFO Land Zones': landZoneBoundaryLayer,
    'Selected WFO Marine Zones': marineZoneBoundaryLayer,
    'NWS API Warning/Alert Polygons': warningLayer
  };

  L.control.layers(null, overlays, { collapsed: false }).addTo(map);

  eventLayer = L.geoJSON(null, {
    pointToLayer: function (feature, latlng) {
      return L.circleMarker(latlng, { radius: 8, weight: 2, opacity: 1, fillOpacity: 0.75 });
    },
    onEachFeature: function (feature, layer) {
      const properties = feature.properties || {};
      const popupHtml = [
        '<strong>' + escapeHtml(properties.report_type || properties.event_type || 'Candidate Report') + '</strong>',
        escapeHtml(properties.county_or_zone || ''),
        escapeHtml(properties.city || ''),
        escapeHtml(properties.valid_utc || properties.begin_time_utc || ''),
        escapeHtml((properties.magnitude ?? '') + ' ' + (properties.magnitude_units || '')),
        '<small>' + escapeHtml(properties.event_narrative || '') + '</small>'
      ].join('<br>');
      layer.bindPopup(popupHtml);
    }
  }).addTo(map);

  loadAllCwaBoundaries();
  setTimeout(function () { map.invalidateSize(); }, 100);
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
  rows.push('<strong>' + escapeHtml(name || 'Boundary Feature') + '</strong>');
  if (state) rows.push('State: ' + escapeHtml(state));
  if (zone) rows.push('Zone/ID: ' + escapeHtml(zone));
  if (wfo) rows.push('WFO/CWA: ' + escapeHtml(wfo));
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

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) return null;
  return response.json();
}

async function loadAllCwaBoundaries() {
  const boundaryStatus = document.getElementById('boundary-status');
  const geojson = await fetchJson('data/boundaries/all_cwas.geojson');
  if (!geojson) {
    if (boundaryStatus) boundaryStatus.textContent = 'All CWA boundaries have not been generated yet. Run the boundary build workflow.';
    return;
  }
  allCwaBoundaryLayer.clearLayers();
  makeBoundaryGeoJsonLayer(geojson, boundaryStyles.all_cwas).addTo(allCwaBoundaryLayer);
  if (boundaryStatus) boundaryStatus.textContent = 'Loaded all CWA boundaries. Select a WFO/month/year to load WFO-specific counties/zones and Storm Data prep files.';
}

async function loadOneWfoBoundaryLayer(path, targetGroup, style) {
  targetGroup.clearLayers();
  const geojson = await fetchJson(path);
  if (!geojson) return false;
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
  results.push({ label: 'selected CWA', loaded: await loadOneWfoBoundaryLayer(basePath + '/cwa.geojson', selectedCwaBoundaryLayer, boundaryStyles.selected_cwa) });
  results.push({ label: 'counties/parishes', loaded: await loadOneWfoBoundaryLayer(basePath + '/counties_parishes.geojson', countyBoundaryLayer, boundaryStyles.counties) });
  results.push({ label: 'land zones', loaded: await loadOneWfoBoundaryLayer(basePath + '/land_zones.geojson', landZoneBoundaryLayer, boundaryStyles.land_zones) });
  results.push({ label: 'marine zones', loaded: await loadOneWfoBoundaryLayer(basePath + '/marine_zones.geojson', marineZoneBoundaryLayer, boundaryStyles.marine_zones) });

  if (!map.hasLayer(countyBoundaryLayer)) countyBoundaryLayer.addTo(map);
  if (!map.hasLayer(landZoneBoundaryLayer)) landZoneBoundaryLayer.addTo(map);
  if (!map.hasLayer(marineZoneBoundaryLayer)) marineZoneBoundaryLayer.addTo(map);

  const loaded = results.filter(item => item.loaded).map(item => item.label);
  if (boundaryStatus) {
    boundaryStatus.textContent = loaded.length > 0
      ? 'Loaded ' + escapeHtml(wfo) + ' boundary layers: ' + loaded.join(', ') + '.'
      : 'No WFO-specific boundary layers found for ' + escapeHtml(wfo) + '. Run the boundary build workflow.';
  }
  setTimeout(function () { map.invalidateSize(); }, 100);
}

async function loadReportGeoJson(path) {
  initializeMap();
  eventLayer.clearLayers();
  const geojson = await fetchJson(path);
  if (!geojson) throw new Error('Reports GeoJSON file not found: ' + path);
  eventLayer.addData(geojson);
  setTimeout(function () {
    map.invalidateSize();
    const bounds = eventLayer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 10 });
  }, 100);
}

async function loadWarningsGeoJson(path) {
  warningLayer.clearLayers();
  const geojson = await fetchJson(path);
  if (!geojson) return false;
  L.geoJSON(geojson, {
    style: { color: '#dc2626', weight: 2, opacity: 0.9, fillOpacity: 0.08 },
    onEachFeature: function (feature, layer) {
      const properties = feature.properties || {};
      layer.bindPopup([
        '<strong>' + escapeHtml(properties.event || 'NWS Alert') + '</strong>',
        escapeHtml(properties.headline || ''),
        escapeHtml(properties.effective || ''),
        escapeHtml(properties.expires || ''),
        '<small>' + escapeHtml(properties.description || '') + '</small>'
      ].join('<br>'));
    }
  }).addTo(warningLayer);
  if (!map.hasLayer(warningLayer)) warningLayer.addTo(map);
  return true;
}

function renderReportTable(reports) {
  if (!reports || reports.length === 0) return '<p>No candidate reports found.</p>';
  const rows = reports.map(report => '<tr>' +
    '<td>' + escapeHtml(report.valid_utc || '') + '</td>' +
    '<td>' + escapeHtml(report.report_type || '') + '</td>' +
    '<td>' + escapeHtml([report.city, report.county, report.state].filter(Boolean).join(', ')) + '</td>' +
    '<td>' + escapeHtml(report.magnitude ?? '') + '</td>' +
    '<td>' + escapeHtml(report.source || '') + '</td>' +
    '<td>' + escapeHtml(report.remark || '') + '</td>' +
    '</tr>').join('');
  return '<table><thead><tr><th>Time UTC</th><th>Report Type</th><th>Location</th><th>Magnitude</th><th>Source</th><th>Remark</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

function renderProductLinks(productCollections) {
  if (!productCollections) return '<p>No product link collection available.</p>';
  const primary = productCollections.primary_links || [];
  const groups = productCollections.product_groups || [];
  const primaryHtml = primary.map(link => '<li><a href="' + escapeHtml(link.url) + '" target="_blank" rel="noopener">' + escapeHtml(link.label) + '</a><br><small>' + escapeHtml(link.note || '') + '</small></li>').join('');
  const groupHtml = groups.map(group => {
    const links = (group.links || []).map(link => '<a class="product-pill" href="' + escapeHtml(link.url) + '" target="_blank" rel="noopener">' + escapeHtml(link.pil) + '</a>').join('');
    return '<div class="product-group"><h3>' + escapeHtml(group.group) + '</h3><p>' + escapeHtml(group.purpose || '') + '</p><div class="product-pills">' + links + '</div></div>';
  }).join('');
  return '<h3>Primary source links</h3><ul>' + primaryHtml + '</ul>' + groupHtml;
}

document.getElementById('load-button').addEventListener('click', async function () {
  const month = document.getElementById('month-select').value;
  const year = document.getElementById('year-input').value;
  const wfo = document.getElementById('wfo-input').value.trim().toUpperCase();

  const statusPanel = document.getElementById('status-panel');
  const summaryPanel = document.getElementById('summary-panel');
  const eventsTable = document.getElementById('events-table');

  const basePath = 'data/stormprep/' + year + '/' + month + '/' + wfo;
  const dashboardPath = basePath + '/dashboard.json';
  const reportsPath = basePath + '/reports.geojson';
  const warningsPath = basePath + '/warnings.geojson';

  statusPanel.innerHTML = '<h2>Status</h2><p>Loading Storm Data prep package: ' + escapeHtml(dashboardPath) + '</p>';

  try {
    await loadWfoBoundaryLayers(wfo);
    const dashboard = await fetchJson(dashboardPath);
    if (!dashboard) throw new Error('Storm Data prep package not found: ' + dashboardPath);

    const summary = dashboard.summary || {};
    const warnings = dashboard.source_warnings || [];

    summaryPanel.innerHTML = '<h2>Summary</h2>' +
      '<p><strong>Mode:</strong> Storm Data prep</p>' +
      '<p><strong>WFO:</strong> ' + escapeHtml(wfo) + '</p>' +
      '<p><strong>Month:</strong> ' + escapeHtml(year + '-' + month) + '</p>' +
      '<p><strong>Candidate reports:</strong> ' + escapeHtml(summary.total_candidate_reports ?? 0) + '</p>' +
      '<p><strong>Mapped reports:</strong> ' + escapeHtml(summary.mapped_candidate_reports ?? 0) + '</p>' +
      '<p><strong>NWS API alerts:</strong> ' + escapeHtml(summary.nws_api_alert_count ?? 0) + '</p>' +
      (warnings.length ? '<p><strong>Source warnings:</strong> ' + escapeHtml(warnings.join(' | ')) + '</p>' : '');

    eventsTable.innerHTML = '<h2>Candidate reports</h2>' + renderReportTable(dashboard.candidate_reports || []) +
      '<h2>Public product links</h2>' + renderProductLinks(dashboard.product_collections);

    await loadReportGeoJson(reportsPath);
    await loadWarningsGeoJson(warningsPath);

    statusPanel.innerHTML = '<h2>Status</h2><p>Loaded Storm Data prep package for ' + escapeHtml(wfo) + ' ' + escapeHtml(year + '-' + month) + '.</p>';
  } catch (error) {
    statusPanel.innerHTML = '<h2>Status</h2><p>' + escapeHtml(error.message) + '</p>' +
      '<p>Run the <strong>Build Storm Data Prep Month</strong> GitHub Action for this year/month/WFO, then refresh the page.</p>';
    summaryPanel.innerHTML = '<h2>Summary</h2><p>No prep package loaded.</p>';
    eventsTable.innerHTML = '<p>No candidate report table available.</p>';
  }
});

window.addEventListener('load', function () { initializeMap(); });
window.addEventListener('resize', function () { if (map) map.invalidateSize(); });
