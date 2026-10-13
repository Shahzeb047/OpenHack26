document.querySelectorAll('form[data-confirm]').forEach(f =>
  f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));

document.querySelectorAll('[data-ms]').forEach(card => {
  card.querySelectorAll('button[data-status]').forEach(btn => btn.addEventListener('click', async () => {
    try {
      const r = await fetch('/api/milestones/' + card.dataset.ms, {
        method: 'PATCH', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content},
        body: JSON.stringify({status: btn.dataset.status})});
      const d = await r.json();
      if (!r.ok) { alert(d.error); return; }
      card.querySelectorAll('button[data-status]').forEach(b => b.setAttribute('aria-pressed', b === btn));
      document.getElementById('progress').textContent = `${d.completed} of ${d.total} completed (${d.percent}%)`;
    } catch { alert('Could not save. Is the server running?'); }
  }));
});
