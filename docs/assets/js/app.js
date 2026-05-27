document.getElementById('load-button').addEventListener('click', () => {
  const month = document.getElementById('month-select').value;
  const year = document.getElementById('year-input').value;
  const wfo = document.getElementById('wfo-input').value.trim().toUpperCase();

  const statusPanel = document.getElementById('status-panel');

  statusPanel.innerHTML = `
    <h2>Status</h2>
    <p>Requested: ${wfo} for ${year}-${month}</p>
    <p>Real Storm Data loading will be added in a future phase.</p>
  `;
});
