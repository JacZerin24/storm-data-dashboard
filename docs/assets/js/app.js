document.getElementById('load-button').addEventListener('click', async () => {
  const month = document.getElementById('month-select').value;
  const year = document.getElementById('year-input').value;
  const wfo = document.getElementById('wfo-input').value.trim().toUpperCase();

  const statusPanel = document.getElementById('status-panel');
  const summaryPanel = document.getElementById('summary-panel');
  const eventsTable = document.getElementById('events-table');

  const eventsPath = `data/stormdata/${year}/${month}/${wfo}/events.json`;

  statusPanel.innerHTML = `
    <h2>Status</h2>
    <p>Loading: ${eventsPath}</p>
  `;

  try {
    const response = await fetch(eventsPath);

    if (!response.ok) {
      throw new Error(`File not found: ${eventsPath}`);
    }

    const data = await response.json();
    const events = data.events || [];

    statusPanel.innerHTML = `
      <h2>Status</h2>
      <p>Loaded ${events.length} event(s) for ${wfo} ${year}-${month}.</p>
    `;

    summaryPanel.innerHTML = `
      <h2>Summary</h2>
      <p><strong>WFO:</strong> ${data.metadata.wfo}</p>
      <p><strong>Month:</strong> ${data.metadata.year}-${String(data.metadata.month).padStart(2, '0')}</p>
      <p><strong>Total events:</strong> ${events.length}</p>
      <p><strong>Schema version:</strong> ${data.metadata.schema_version}</p>
    `;

    if (events.length === 0) {
      eventsTable.innerHTML = '<p>No events found.</p>';
      return;
    }

    eventsTable.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Time UTC</th>
            <th>Type</th>
            <th>Location</th>
            <th>Magnitude</th>
            <th>Narrative</th>
          </tr>
        </thead>
        <tbody>
          ${events.map(event => `
            <tr>
              <td>${event.begin_time_utc || ''}</td>
              <td>${event.event_type || ''}</td>
              <td>${event.county_or_zone || event.cz_name || ''}</td>
              <td>${event.magnitude ?? ''} ${event.magnitude_units || ''}</td>
              <td>${event.event_narrative || ''}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (error) {
    statusPanel.innerHTML = `
      <h2>Status</h2>
      <p>${error.message}</p>
      <p>This usually means that sample data has not been created for that year/month/WFO yet.</p>
    `;

    summaryPanel.innerHTML = `
      <h2>Summary</h2>
      <p>No data loaded.</p>
    `;

    eventsTable.innerHTML = `
      <p>No event table available.</p>
    `;
  }
});
