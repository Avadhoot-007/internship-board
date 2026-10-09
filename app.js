const $ = id => document.getElementById(id);
const DATA_URL = './internships.json';
const KEY = 'applications';
let items = [], current = null, opener = null;

function esc(s){ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

async function load(){
  $('list').innerHTML = '<p class="state" role="status">Loading internships…</p>';
  $('count').textContent = '';
  try {
    // add ?fail=1 to the page URL to test the error state
    if (new URLSearchParams(location.search).has('fail')) throw new Error('Simulated failure');
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const json = await res.json();
    items = json.internships;
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

const field = { name: 'e-name', email: 'e-email', url: 'e-url' };
function clearErrors(){ Object.values(field).forEach(id => $(id).textContent = ''); ['a-name','a-email','a-url'].forEach(id => $(id).removeAttribute('aria-invalid')); }

function validate(v){
  const err = {};
  if (!v.name.trim()) err.name = 'Enter your full name.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.email)) err.email = 'Enter a valid email, like name@example.com.';
  if (v.url.trim()){
    try { if (new URL(v.url).protocol !== 'https:') throw 0; } catch { err.url = 'Enter a full https:// link, or leave this empty.'; }
  }
  return err;
}

$('apply').addEventListener('submit', e => {
  e.preventDefault();
  clearErrors();
  const v = { name: $('a-name').value, email: $('a-email').value, url: $('a-url').value };
  const err = validate(v);
  const keys = Object.keys(err);
  if (keys.length){
    keys.forEach(k => { $(field[k]).textContent = err[k]; $('a-' + k).setAttribute('aria-invalid', 'true'); });
    $('a-' + keys[0]).focus();
    return;
  }
  const saved = JSON.parse(localStorage.getItem(KEY) || '[]');
  const email = v.email.trim().toLowerCase();
  if (saved.some(a => a.id === current.id && a.email === email)){
    $('a-msg').textContent = 'You already applied to this role with that email.';
    return;
  }
  saved.push({ id: current.id, email });
  localStorage.setItem(KEY, JSON.stringify(saved));
  $('a-msg').textContent = 'Application sent for ' + current.title + '.';
  $('apply').reset();
});

load();
