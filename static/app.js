const $ = (id) => document.getElementById(id);
const API_LIST = "api/internships";
const API_APPLY = "api/applications";
const TIMEOUT_MS = 10000;
let items = [],
  current = null,
  opener = null,
  sending = false;

function esc(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}

// Returns { ok, status, body }. Throws on network error or timeout.
async function request(url, options = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      ...options,
      credentials: "omit",
      signal: ctrl.signal,
    });
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    return { ok: res.ok, status: res.status, body };
  } finally {
    clearTimeout(timer);
  }
}

async function load() {
  $("list").innerHTML =
    '<p class="state" role="status">Loading internships…</p>';
  $("count").textContent = "";
  try {
    // add ?fail=1 to the page URL to test the error state
    if (new URLSearchParams(location.search).has("fail"))
      throw new Error("Simulated failure");
    const res = await request(API_LIST);
    if (!res.ok || !res.body || !Array.isArray(res.body.internships))
      throw new Error("HTTP " + res.status);
    items = res.body.internships;
    fillOptions("domain", [...new Set(items.map((i) => i.domain))]);
    fillOptions("mode", [...new Set(items.map((i) => i.mode))]);
    render();
  } catch (e) {
    showLoadError();
  }
}

function showLoadError() {
  $("list").innerHTML =
    '<div class="state error" role="alert"><p>Could not load internships. Check your connection and try again.</p><button type="button" id="retry">Retry</button></div>';
  $("retry").addEventListener("click", load);
  $("retry").focus();
}

function fillOptions(id, values) {
  const sel = $(id);
  sel.length = 1;
  values.forEach((v) => sel.add(new Option(v, v)));
}

function render() {
  const q = $("q").value.trim().toLowerCase(),
    d = $("domain").value,
    m = $("mode").value;
  const hits = items.filter(
    (i) =>
      (!d || i.domain === d) &&
      (!m || i.mode === m) &&
      (!q || (i.title + " " + i.skills.join(" ")).toLowerCase().includes(q)),
  );
  $("count").textContent =
    hits.length +
    (hits.length === 1 ? " internship found" : " internships found");
  if (!hits.length) {
    $("list").innerHTML =
      '<div class="state"><p>No internships match. Clear a filter or try another skill.</p><button type="button" id="clear">Clear filters</button></div>';
    $("clear").addEventListener("click", () => {
      $("q").value = "";
      $("domain").value = "";
      $("mode").value = "";
      render();
      $("q").focus();
    });
    return;
  }
  // Button holds only phrasing content; the heading wraps the button.
  $("list").innerHTML = hits
    .map(
      (i) => `
    <h2 class="card-h">
      <button type="button" class="card" data-id="${esc(i.id)}">
        <span class="card-title">${esc(i.title)}</span>
        <span class="meta">${esc(i.domain)} · ${esc(i.mode)} · ${esc(i.location)}</span>
        <span class="meta">${i.openings} ${i.openings === 1 ? "opening" : "openings"}</span>
        <span class="chips">${i.skills.map((s) => `<span>${esc(s)}</span>`).join("")}</span>
      </button>
    </h2>`,
    )
    .join("");
}

$("filters").addEventListener("submit", (e) => e.preventDefault());
["q", "domain", "mode"].forEach((id) =>
  $(id).addEventListener("input", render),
);

$("list").addEventListener("click", (e) => {
  const card = e.target.closest(".card");
  if (!card) return;
  opener = card;
  current = items.find((i) => i.id === card.dataset.id);
  if (!current) return;
  $("d-title").textContent = current.title;
  $("d-meta").textContent =
    `${current.domain} · ${current.mode} · ${current.location} · ${current.openings} open`;
  $("d-skills").className = "chips";
  $("d-skills").innerHTML = current.skills
    .map((s) => `<li>${esc(s)}</li>`)
    .join("");
  $("apply").reset();
  clearErrors();
  $("a-msg").textContent = "";
  $("detail").showModal();
});
$("close").addEventListener("click", () => $("detail").close());
$("detail").addEventListener("close", () => opener && opener.focus());

const field = { name: "e-name", email: "e-email", url: "e-url" };
const inputFor = { name: "a-name", email: "a-email", url: "a-url" };

function clearErrors() {
  Object.values(field).forEach((id) => ($(id).textContent = ""));
  Object.values(inputFor).forEach((id) =>
    $(id).removeAttribute("aria-invalid"),
  );
}

function showFieldErrors(err) {
  const keys = Object.keys(err);
  keys.forEach((k) => {
    $(field[k]).textContent = err[k];
    $(inputFor[k]).setAttribute("aria-invalid", "true");
  });
  $(inputFor[keys[0]]).focus();
}

// Client checks are UX only. The server validates again.
function validate(v) {
  const err = {};
  const name = v.name.trim();
  if (name.length < 2 || name.length > 100)
    err.name = "Enter your full name, 2 to 100 characters.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.email.trim()))
    err.email = "Enter a valid email, like name@example.com.";
  if (v.url.trim()) {
    try {
      if (new URL(v.url.trim()).protocol !== "https:") throw 0;
    } catch {
      err.url = "Enter a full https:// link, or leave this empty.";
    }
  }
  return err;
}

function setSending(on) {
  const btn = $("apply").querySelector('button[type="submit"]');
  btn.disabled = on;
  btn.textContent = on ? "Sending…" : "Send application";
}

// Map server responses to form messages.
function showServerError(res) {
  const b = res.body || {};
  if (res.status === 400 && b.errors) {
    const fieldErr = {};
    let msg = "";
    for (const [key, text] of Object.entries(b.errors)) {
      if (field[key]) fieldErr[key] = text;
      else msg = text;
    }
    if (Object.keys(fieldErr).length) showFieldErrors(fieldErr);
    $("a-msg").textContent =
      msg ||
      (Object.keys(fieldErr).length ? "" : "Check your details and try again.");
    return;
  }
  const messages = {
    404: "This role is no longer available.",
    409: b.error || "You already applied to this role with that email.",
    413: "Your request was too large. Shorten your entries.",
    429: "Too many attempts. Wait a minute and try again.",
  };
  if (res.status >= 500)
    $("a-msg").textContent = "Server error. Try again later.";
  else
    $("a-msg").textContent =
      messages[res.status] || b.error || "Could not send. Try again.";
}

$("apply").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (sending) return;
  clearErrors();
  $("a-msg").textContent = "";
  const v = {
    name: $("a-name").value,
    email: $("a-email").value,
    url: $("a-url").value,
  };
  const err = validate(v);
  if (Object.keys(err).length) {
    showFieldErrors(err);
    return;
  }

  sending = true;
  setSending(true);
  try {
    const res = await request(API_APPLY, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        internship_id: current.id,
        name: v.name.trim(),
        email: v.email.trim(),
        url: v.url.trim(),
      }),
    });
    if (res.status === 201) {
      $("a-msg").textContent = "Application sent for " + current.title + ".";
      $("apply").reset();
    } else {
      showServerError(res);
    }
  } catch {
    $("a-msg").textContent =
      "Network problem. Check your connection and try again.";
  } finally {
    sending = false;
    setSending(false);
  }
});

load();
