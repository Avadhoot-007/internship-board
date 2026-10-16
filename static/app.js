const $ = id => document.getElementById(id);
const API = { list: '/api/internships', apply: '/api/applications' };
const TIMEOUT_MS = 10000;
let items = [], current = null, opener = null, sending = false;

function esc(s){ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// Wraps fetch with a timeout. Returns { ok, status, body }. Throws on network failure or timeout.
async function requestJSON(url, opts = {}){
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      ...opts,
      signal: ctrl.signal,
      headers: { Accept: 'application/json', ...(opts.headers || {}) },
      credentials: 'omit',
    });
    const body = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, body };
  } finally {
    clearTimeout(timer);
  }
}

async function load(){
  $('list').innerHTML = '<p class="state" role="status">Loading internships…</p>';
  $('count').textContent = '';
  try {
    // add ?fail=1 to the page URL to test the error state
    if (new URLSearchParams(location.search).has('fail')) throw new Error('Simulated failure');
    const r = await requestJSON(API.list);
    if (!r.ok || !Array.isArray(r.body.internships)) throw new Error('HTTP ' + r.status);
    items = r.body.internships;
    fillOptions('domain', [...new Set(items.map(i => i.domain))]);
    fillOptions('mode', [...new Set(items.map(i => i.mode))]);
    render();
  } catch (e) {
    $('list').innerHTML = '<div class="state error" role="alert"><p>Could not load internships. Check your connection and try again.</p><button type="button" id="retry">Retry</button></div>';
    $('retry').addEventListener('click', load);
    $('retry').focus();
  }
}

function fillOptions(id, values){
  const sel = $(id);
  sel.length = 1;
  values.forEach(v => sel.add(new Option(v, v)));
}

function render(){
  const q = $('q').value.trim().toLowerCase(), d = $('domain').value, m = $('mode').value;
  const hits = items.filter(i =>
    (!d || i.domain === d) && (!m || i.mode === m) &&
    (!q || (i.title + ' ' + i.skills.join(' ')).toLowerCase().includes(q)));
  $('count').textContent = hits.length + (hits.length === 1 ? ' internship found' : ' internships found');
  if (!hits.length){
    $('list').innerHTML = '<div class="state"><p>No internships match. Clear a filter or try another skill.</p><button type="button" id="clear">Clear filters</button></div>';
    $('clear').addEventListener('click', () => { $('q').value = ''; $('domain').value = ''; $('mode').value = ''; render(); $('q').focus(); });
    return;
  }
  $('list').innerHTML = hits.map(i => `
    <button type="button" class="card" data-id="${esc(i.id)}">
      <h2>${esc(i.title)}</h2>
      <p class="meta">${esc(i.domain)} · ${esc(i.mode)} · ${esc(i.location)}</p>
      <p class="meta">${i.openings} ${i.openings === 1 ? 'opening' : 'openings'}</p>
      <ul class="chips">${i.skills.map(s => `<li>${esc(s)}</li>`).join('')}</ul>
    </button>`).join('');
}

$('filters').addEventListener('submit', e => e.preventDefault());
['q','domain','mode'].forEach(id => $(id).addEventListener('input', render));

$('list').addEventListener('click', e => {
  const card = e.target.closest('.card');
  if (!card) return;
  opener = card;
  current = items.find(i => i.id === card.dataset.id);
  $('d-title').textContent = current.title;
  $('d-meta').textContent = `${current.domain} · ${current.mode} · ${current.location} · ${current.openings} open`;
  $('d-skills').className = 'chips';
  $('d-skills').innerHTML = current.skills.map(s => `<li>${esc(s)}</li>`).join('');
  $('apply').reset(); clearErrors(); $('a-msg').textContent = '';
  $('detail').showModal();
});
$('close').addEventListener('click', () => $('detail').close());
$('detail').addEventListener('close', () => opener && opener.focus());

// Client-side checks are for fast feedback only. The server re-validates everything.
const field = { name: 'e-name', email: 'e-email', url: 'e-url' };
function clearErrors(){
  Object.values(field).forEach(id => $(id).textContent = '');
  ['a-name','a-email','a-url'].forEach(id => $(id).removeAttribute('aria-invalid'));
}

function validate(v){
  const err = {};
  if (v.name.length < 2 || v.name.length > 100 || ![...v.name].every(c => /[\p{L}\p{M} .'\-]/u.test(c)))
    err.name = 'Use 2 to 100 letters, spaces, dots, apostrophes or hyphens.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.email)) err.email = 'Enter a valid email, like name@example.com.';
  if (v.url){
    try { if (new URL(v.url).protocol !== 'https:') throw 0; } catch { err.url = 'Enter a full https:// link, or leave this empty.'; }
  }
  return err;
}

function showFieldErrors(errs){
  let first = null;
  Object.entries(errs).forEach(([k, msg]) => {
    if (field[k]){
      $(field[k]).textContent = msg;
      const input = $('a-' + k);
      input.setAttribute('aria-invalid', 'true');
      first = first || input;
    } else {
      $('a-msg').textContent = msg;
    }
  });
  if (first) first.focus();
}

function setSending(on){
  sending = on;
  $('submit').disabled = on;
  $('submit').textContent = on ? 'Sending…' : 'Send application';
  $('apply').setAttribute('aria-busy', String(on));
}

$('apply').addEventListener('submit', async e => {
  e.preventDefault();
  if (sending) return;
  clearErrors();
  $('a-msg').textContent = '';

  const v = {
    internship_id: current.id,
    name: $('a-name').value.trim(),
    email: $('a-email').value.trim(),
    url: $('a-url').value.trim(),
  };
  const clientErrs = validate(v);
  if (Object.keys(clientErrs).length) return showFieldErrors(clientErrs);

  setSending(true);
  try {
    const r = await requestJSON(API.apply, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(v),
    });
    if (r.status === 201){
      $('a-msg').textContent = 'Application sent for ' + current.title + '.';
      $('apply').reset();
    } else if (r.status === 400 && r.body.errors){
      showFieldErrors(r.body.errors);
    } else if (r.status === 409){
      $('a-msg').textContent = r.body.error;
    } else if (r.status === 429){
      $('a-msg').textContent = 'Too many attempts. Wait a minute, then retry.';
    } else if (r.status === 404){
      $('a-msg').textContent = 'This internship is no longer listed.';
    } else {
      $('a-msg').textContent = 'Could not send. Try again.';
    }
  } catch {
    $('a-msg').textContent = 'Network problem. Check your connection and retry.';
  } finally {
    setSending(false);
  }
});

load();
