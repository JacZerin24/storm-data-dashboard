let map;
let eventLayer;
let warningLayer;
let tornadoTrackLayer;
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

const reportStyles = {
  marine: { color: '#38bdf8', fillColor: '#7dd3fc' },
  hail: { color: '#15803d', fillColor: '#22c55e' },
  thunderstorm_wind: { color: '#1e3a8a', fillColor: '#2563eb' },
  tornado: { color: '#991b1b', fillColor: '#dc2626' },
  flooding: { color: '#064e3b', fillColor: '#047857' },
  heat_cold: { color: '#c2410c', fillColor: '#fb923c' },
  winter: { color: '#0f766e', fillColor: '#2dd4bf' },
  fire_smoke: { color: '#7c2d12', fillColor: '#f97316' },
  other: { color: '#374151', fillColor: '#9ca3af' }
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function normalizeCategory(properties) {
  const category = String(properties.event_category || '').toLowerCase();
  const type = String(properties.report_type || properties.event_type || '').toUpperCase();

  if (category === 'marine' || type.includes('MARINE') || type.includes('WATER SPOUT') || type.includes('WATERSPOUT')) return 'marine';
  if (category === 'hail' || type.includes('HAIL')) return 'hail';
  if (category === 'tornado' || type.includes('TORNADO')) return 'tornado';
  if (category === 'thunderstorm_wind' || type.includes('TSTM WND') || type.includes('THUNDERSTORM WIND') || type.includes('WIND GST') || type.includes('WIND DMG')) return 'thunderstorm_wind';
  if (category === 'flooding' || type.includes('FLASH FLOOD') || type.includes('FLOOD')) return 'flooding';
  if (category && reportStyles[category]) return category;
  return 'other';
}

function styleForReport(properties) {
  const style = reportStyles[normalizeCategory(properties)] || reportStyles.other;
  return {
    radius: 8,
    weight: 2,
    opacity: 1,
    fillOpacity: 0.78,
    color: style.color,
    fillColor: style.fillColor
  };
}

function parseUtcDate(value) {
  if (!value) return null;
  const text = String(value).trim();
  const digits = text.replace(/\D/g, '');

  if (digits.length >= 12 && !text.includes('-')) {
    const year = Number(digits.slice(0, 4));
    const month = Number(digits.slice(4, 6)) - 1;
    const day = Number(digits.slice(6, 8));
    const hour = Number(digits.slice(8, 10));
    const minute = Number(digits.slice(10, 12));
    return new Date(Date.UTC(year, month, day, hour, minute));
  }

  const candidate = text.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(text) ? text : text + 'Z';
  const dt = new Date(candidate);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function standardOffsetForWfo(wfo, lon) {
  const overrides = {
    LIX: [-6, 'CST'], MOB: [-6, 'CST'], JAN: [-6, 'CST'], LCH: [-6, 'CST'], SHV: [-6, 'CST'], HGX: [-6, 'CST'], FWD: [-6, 'CST'], EWX: [-6, 'CST'], CRP: [-6, 'CST'], BRO: [-6, 'CST'],
    MFL: [-5, 'EST'], MLB: [-5, 'EST'], JAX: [-5, 'EST'], TAE: [-5, 'EST'], TBW: [-5, 'EST'], KEY: [-5, 'EST'], CHS: [-5, 'EST'], ILM: [-5, 'EST'], MHX: [-5, 'EST'], RAH: [-5, 'EST'],
    OUN: [-6, 'CST'], TSA: [-6, 'CST'], SGF: [-6, 'CST'], LSX: [-6, 'CST'], EAX: [-6, 'CST'], ICT: [-6, 'CST'], TOP: [-6, 'CST'],
    ABQ: [-7, 'MST'], EPZ: [-7, 'MST'], FGZ: [-7, 'MST'], PSR: [-7, 'MST'], TWC: [-7, 'MST'], SLC: [-7, 'MST'], BOU: [-7, 'MST'], PUB: [-7, 'MST'], CYS: [-7, 'MST'], RIW: [-7, 'MST'],
    LOX: [-8, 'PST'], SGX: [-8, 'PST'], MTR: [-8, 'PST'], STO: [-8, 'PST'], HNX: [-8, 'PST'], EKA: [-8, 'PST'], MFR: [-8, 'PST'], PQR: [-8, 'PST'], SEW: [-8, 'PST'], OTX: [-8, 'PST'],
    AFG: [-9, 'AKST'], AJK: [-9, 'AKST'], AFC: [-9, 'AKST'], HFO: [-10, 'HST'], SJU: [-4, 'AST'], GUM: [10, 'ChST'], PPG: [-11, 'SST']
  };

  if (overrides[wfo]) return overrides[wfo];
  if (typeof lon === 'number') {
    if (lon <= -130) return [-9, 'AKST'];
    if (lon <= -114) return [-8, 'PST'];
    if (lon <= -102) return [-7, 'MST'];
    if (lon <= -85) return [-6, 'CST'];
    if (lon <= -60) return [-5, 'EST'];
  }
  return [0, 'UTC'];
}

function formatUtc(value) {
  const dt = parseUtcDate(value);
  if (!dt) return value || '';
  return dt.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
}

function formatStandardTime(value, wfo, lon) {
  const dt = parseUtcDate(value);
  if (!dt) return '';
  const [offset, label] = standardOffsetForWfo(wfo, lon);
  const shifted = new Date(dt.getTime() + offset * 60 * 60 * 1000);
  return shifted.toISOString().slice(0, 16).replace('T', ' ') + ' ' + label;
}

function formatTimePair(value, wfo, lon, providedStandard) {
  const st = providedStandard || formatStandardTime(value, wfo, lon);
  const utc = formatUtc(value);
  if (st && utc) return st + '<br><small>' + escapeHtml(utc) + '</small>';
  return escapeHtml(utc || value || '');
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
  tornadoTrackLayer = L.layerGroup();

  const overlays = {
    'All CWA Boundaries': allCwaBoundaryLayer,
    'Selected WFO CWA': selectedCwaBoundaryLayer,
    'Selected WFO Counties/Parishes': countyBoundaryLayer,
    'Selected WFO Land Zones': landZoneBoundaryLayer,
    'Selected WFO Marine Zones': marineZoneBoundaryLayer,
    'NWS API Warning/Alert Polygons': warningLayer,
    'Tornado Tracks / DAT Tracks': tornadoTrackLayer
  };

  L.control.layers(null, overlays, { collapsed: false }).addTo(map);
  addLegend();

  eventLayer = L.geoJSON(null, {
    pointToLayer: function (feature, latlng) {
      return L.circleMarker(latlng, styleForReport(feature.properties || {}));
    },
    onEachFeature: function (feature, layer) {
      const properties = feature.properties || {};
      const popupHtml = [
        '<strong>' + escapeHtml(properties.report_type || properties.event_type || 'Candidate Report') + '</strong>',
        escapeHtml([properties.city, properties.county_or_zone, properties.state].filter(Boolean).join(', ')),
        formatTimePair(properties.valid_utc || properties.begin_time_utc, properties.wfo, feature.geometry?.coordinates?.[0], properties.standard_time_display),
        escapeHtml((properties.magnitude ?? '') + ' ' + (properties.magnitude_units || '')),
        '<small>' + escapeHtml(properties.event_narrative || '') + '</small>'
      ].join('<br>');
      layer.bindPopup(popupHtml);
    }
  }).addTo(map);

  loadAllCwaBoundaries();
  setTimeout(function () { map.invalidateSize(); }, 100);
}

function addLegend() {
  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = function () {
    const div = L.DomUtil.create('div', 'map-legend');
    div.innerHTML = '<strong>Candidate Reports</strong>' +
      '<div><span style="background:#dc2626"></span>Tornado</div>' +
      '<div><span style="background:#22c55e"></span>Hail</div>' +
      '<div><span style="background:#2563eb"></span>Land wind/gust/damage</div>' +
      '<div><span style="background:#047857"></span>Flash flooding/flooding</div>' +
      '<div><span style="background:#7dd3fc"></span>Marine</div>' +
      '<div><span style="background:#9ca3af"></span>Other</div>';
    return div;
  };
  legend.addTo(map);
}

function getFirstProperty(properties, names) {
  for (const name of names) {
    if (properties[name] !== undefined && properties[name] !== null && properties[name] !== '') return properties[name];
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
        formatTimePair(properties.effective, null, null, null),
        formatTimePair(properties.expires, null, null, null),
        '<small>' + escapeHtml(properties.description || '') + '</small>'
      ].join('<br>'));
    }
  }).addTo(warningLayer);
  if (!map.hasLayer(warningLayer)) warningLayer.addTo(map);
  return true;
}

async function loadTornadoTracksGeoJson(path) {
  tornadoTrackLayer.clearLayers();
  const geojson = await fetchJson(path);
  if (!geojson) return false;
  L.geoJSON(geojson, {
    style: { color: '#b91c1c', weight: 4, opacity: 0.95, fillOpacity: 0.12 },
    pointToLayer: function (feature, latlng) {
      return L.circleMarker(latlng, { radius: 6, weight: 2, color: '#b91c1c', fillColor: '#ef4444', fillOpacity: 0.85 });
    },
    onEachFeature: function (feature, layer) {
      const properties = feature.properties || {};
      layer.bindPopup([
        '<strong>' + escapeHtml(properties.label || properties.event_type || 'Tornado Track') + '</strong>',
        escapeHtml(properties.rating || ''),
        escapeHtml(properties.source || ''),
        '<small>' + escapeHtml(properties.note || '') + '</small>'
      ].join('<br>'));
    }
  }).addTo(tornadoTrackLayer);
  if (!map.hasLayer(tornadoTrackLayer)) tornadoTrackLayer.addTo(map);
  return true;
}

function renderReportTable(reports) {
  if (!reports || reports.length === 0) return '<p>No candidate reports found.</p>';
  const rows = reports.map(report => '<tr>' +
    '<td>' + formatTimePair(report.valid_utc, report.wfo, report.lon, report.standard_time_display) + '</td>' +
    '<td><span class="report-chip report-chip-' + escapeHtml(report.event_category || 'other') + '"></span>' + escapeHtml(report.report_type || '') + '</td>' +
    '<td>' + escapeHtml([report.city, report.county, report.state].filter(Boolean).join(', ')) + '</td>' +
    '<td>' + escapeHtml(report.magnitude ?? '') + '</td>' +
    '<td>' + escapeHtml(report.source || '') + '</td>' +
    '<td>' + escapeHtml(report.remark || '') + '</td>' +
    '</tr>').join('');
  return '<table><thead><tr><th>Storm Data ST<br><small>UTC below</small></th><th>Report Type</th><th>Location</th><th>Magnitude</th><th>Source</th><th>Remark</th></tr></thead><tbody>' + rows + '</tbody></table>';
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
  const tornadoTracksPath = basePath + '/tornado_tracks.geojson';

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
      '<p><strong>Tornado tracks:</strong> ' + escapeHtml(summary.tornado_track_count ?? 0) + '</p>' +
      (warnings.length ? '<p><strong>Source warnings:</strong> ' + escapeHtml(warnings.join(' | ')) + '</p>' : '');

    eventsTable.innerHTML = '<h2>Candidate reports</h2>' + renderReportTable(dashboard.candidate_reports || []) +
      '<h2>Public product links</h2>' + renderProductLinks(dashboard.product_collections);

    await loadReportGeoJson(reportsPath);
    await loadWarningsGeoJson(warningsPath);
    await loadTornadoTracksGeoJson(tornadoTracksPath);

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
