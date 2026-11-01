/* Koordinátor stránky: načítání stavu a údržby, výběr programu, příkazy. Závisí na api.js. */

/** Jak často se stránka ptá serveru (server odpovídá z cache, myčku nečte). */
const STATUS_REFRESH_MS = 5000;
const MAINT_REFRESH_MS = 60000;

const state = {
  programs: [],    // katalog z /api/programy
  selected: null,  // kód vybraného programu
  stav: null,      // poslední Stav ze serveru
  settingPending: false,  // běží změna nastavení – obnova stavu ovládací prvky nepřepisuje
};

const $ = (id) => document.getElementById(id);

/** Vytvoří prvek s textem (bez innerHTML – data ze serveru se nevkládají jako HTML). */
function el(tag, text, className) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (className) e.className = className;
  return e;
}

/** ISO čas ze serveru → místní čas prohlížeče (s datem, pokud není dnešní). */
function formatTime(iso, withDate = false) {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("cs-CZ", { hour: "2-digit", minute: "2-digit" });
  const today = d.toDateString() === new Date().toDateString();
  return withDate || !today ? `${d.toLocaleDateString("cs-CZ")} ${time}` : time;
}

/** Minuty → „2 h 10 min“. */
function formatMinutes(min) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h} h ${m} min` : `${m} min`;
}

/** Zobrazí výsledek akce (nebo chybu) v prvku `target`. */
function showResult(target, message, isError = false) {
  target.textContent = message;
  target.classList.toggle("err", isError);
  target.hidden = false;
}

/** Text výsledku příkazu: v dry-run plaintext, ostře změny stavu. */
function describeCommand(res) {
  if (!res.odeslano) return `Zkušební režim – neodesláno: ${res.plaintext}`;
  if (res.varovani) return res.varovani;
  const changes = Object.entries(res.zmeny || {}).map(([k, [a, b]]) => `${k} ${a}→${b}`);
  return changes.length ? `Odesláno. Změny: ${changes.join(", ")}`
    : "Odesláno, ale myčka zatím nic nezměnila – zkontrolujte stav.";
}

/* ---------- stav ---------- */

/** Vykreslí kartu stavu podle odpovědi /api/stav. */
function renderStatus(data) {
  $("dry-run").hidden = !data.dry_run;
  $("st-error").hidden = !data.chyba;
  $("st-error").textContent = data.chyba || "";
  $("st-updated").textContent = data.aktualizovano ? `Aktualizováno ${formatTime(data.aktualizovano)}` : "";

  const s = data.stav;
  state.stav = s;
  if (!s) return;

  $("st-label").textContent = s.popis;
  const remote = $("st-remote");
  remote.textContent = s.dalkove_ovladani ? "Dálkové ovládání zapnuto" : "Dálkové ovládání vypnuto";
  remote.className = s.dalkove_ovladani ? "badge badge-ok" : "badge badge-warn";

  const running = s.aktivni;
  $("st-program").textContent = s.program_nazev + (s.volby.length ? ` · ${optionNames(s.program, s.volby)}` : "");
  $("st-phase").textContent = s.faze + (s.dvirka_otevrena ? " · dvířka otevřená" : "");

  const program = state.programs.find((p) => p.kod === s.program);
  const bar = $("st-progress");
  bar.hidden = s.stav !== "beh" && s.stav !== "pauza";
  if (!bar.hidden && program) {
    const total = Math.max(program.delka, s.zbyva_min);
    bar.firstElementChild.style.width = `${Math.round(100 * (1 - s.zbyva_min / total))}%`;
  }

  let timeText = "";
  if (s.stav === "odlozeno") {
    const start = new Date(Date.now() + s.odlozeni_min * 60000);
    timeText = `Start za ${formatMinutes(s.odlozeni_min)} (v ${formatTime(start.toISOString())}), délka ${formatMinutes(s.zbyva_min)}`;
  } else if (running) {
    const end = new Date(Date.now() + s.zbyva_min * 60000);
    timeText = `Zbývá ${formatMinutes(s.zbyva_min)} · konec kolem ${formatTime(end.toISOString())}`;
  } else if (s.stav === "vyber") {
    timeText = `Na panelu vybráno, délka ${formatMinutes(s.zbyva_min)}`;
  }
  $("st-time").textContent = timeText;

  const warnings = $("st-warnings");
  warnings.replaceChildren(...s.varovani.map((w) => el("li", w)));

  $("btn-stop").hidden = !running;
  $("btn-start").disabled = running;
  renderSettings(s.nastaveni);
}

/** České názvy voleb programu. */
function optionNames(code, opts) {
  const program = state.programs.find((p) => p.kod === code);
  const names = new Map((program ? program.volby : []).map((o) => [o.kod, o.nazev]));
  return opts.map((o) => names.get(o) || o).join(", ");
}

/** Načte stav ze serveru; chyba spojení se ukáže v kartě stavu. */
async function loadStatus() {
  try {
    renderStatus(await apiGet("/stav"));
  } catch (err) {
    $("st-error").hidden = false;
    $("st-error").textContent = err.message;
  }
}

/* ---------- výběr programu a start ---------- */

/** Vykreslí tlačítka programů; programy jen z appky jsou neaktivní. */
function renderPrograms() {
  const grid = $("programs");
  grid.replaceChildren(...state.programs.map((p) => {
    const btn = el("button", undefined, "program");
    btn.type = "button";
    btn.dataset.code = p.kod;
    btn.disabled = !p.spustitelny;
    btn.setAttribute("aria-pressed", String(p.kod === state.selected));
    btn.append(el("span", p.nazev, "name"),
      el("span", p.spustitelny ? `${formatMinutes(p.delka)}${p.teplota ? ` · ${p.teplota} °C` : ""}` : "jen z appky", "meta"));
    btn.addEventListener("click", () => selectProgram(p.kod));
    return btn;
  }));
}

/** Vybere program: zvýrazní ho a nabídne jen jeho povolené volby. */
function selectProgram(code) {
  state.selected = code;
  const p = state.programs.find((x) => x.kod === code);
  renderPrograms();
  $("prog-desc").textContent = p.popis;

  const box = $("options");
  box.replaceChildren(el("legend", "Volby"), ...p.volby.map((o) => {
    const label = el("label");
    const input = el("input");
    input.type = "checkbox";
    input.value = o.kod;
    input.addEventListener("change", () => { applyExclusive(p); updatePreview(); });
    label.append(input, document.createTextNode(o.nazev));
    return label;
  }));
  if (!p.volby.length) box.append(el("span", "Program nemá volby.", "muted"));
  updatePreview();
}

/** Zakáže volby, které se vylučují s už zaškrtnutou (ExtraDry ↔ ½ náplň ↔ Eco). */
function applyExclusive(program) {
  const inputs = [...$("options").querySelectorAll("input")];
  const checked = inputs.find((i) => i.checked && program.vylucne.includes(i.value));
  for (const i of inputs) {
    i.disabled = Boolean(checked) && i !== checked && program.vylucne.includes(i.value);
  }
}

/** Vybrané volby. */
function selectedOptions() {
  return [...$("options").querySelectorAll("input:checked")].map((i) => i.value);
}

/**
 * Náhled konce. Stejný výpočet jako server (odložení po půlhodinách, zaokrouhleno);
 * závazný je odhad, který vrátí server po startu.
 */
function updatePreview() {
  const p = state.programs.find((x) => x.kod === state.selected);
  const out = $("start-preview");
  if (!p) { out.textContent = "Vyberte program."; return; }
  const now = new Date();
  if (timingMode() === "now") {
    out.textContent = `Skončí kolem ${formatTime(new Date(now.getTime() + p.delka * 60000).toISOString())}`;
    return;
  }
  const [h, m] = $("end-time").value.split(":").map(Number);
  const target = new Date(now);
  target.setHours(h, m, 0, 0);
  if (target <= now) target.setDate(target.getDate() + 1);
  const waitMin = (target - now) / 60000 - p.delka;
  if (waitMin < 0) { out.textContent = "Do tohoto času program nestihne doběhnout."; return; }
  const halfHours = Math.round(waitMin / 30);
  if (halfHours > 48) { out.textContent = "Odložení může být nejvýš 24 hodin."; return; }
  const end = new Date(now.getTime() + (halfHours * 30 + p.delka) * 60000);
  out.textContent = `Start za ${formatMinutes(halfHours * 30)}, konec kolem ${formatTime(end.toISOString())} (±15 min)`;
}

/** „now“ nebo „end“ podle přepínače Kdy. */
function timingMode() {
  return document.querySelector("input[name=timing]:checked").value;
}

/** Potvrdí a odešle start vybraného programu. */
async function startProgram() {
  const p = state.programs.find((x) => x.kod === state.selected);
  const result = $("start-result");
  if (!p) { showResult(result, "Nejdřív vyberte program.", true); return; }
  const opts = selectedOptions();
  const body = { program: p.kod, volby: opts };
  if (timingMode() === "end") body.konec = $("end-time").value;
  const what = `${p.nazev}${opts.length ? ` (${optionNames(p.kod, opts)})` : ""}`;
  if (!confirm(`Spustit ${what}${body.konec ? `, konec v ${body.konec}` : " hned"}?`)) return;
  try {
    const res = await apiPost("/start", body);
    showResult(result, `${describeCommand(res)} · odhad konce ${formatTime(res.odhad_konce)}`);
    loadStatus();
  } catch (err) {
    showResult(result, err.message, true);
  }
}

/** Zastaví program nebo zruší odložený start. */
async function stopProgram() {
  if (!confirm("Zastavit program?")) return;
  try {
    const res = await apiPost("/stop");
    showResult($("start-result"), describeCommand(res));
    loadStatus();
  } catch (err) {
    showResult($("start-result"), err.message, true);
  }
}

/* ---------- nastavení ---------- */

/**
 * Nastaví ovládací prvky podle skutečného stavu myčky. Během odesílání změny je
 * nepřepisuje; po něm (i po chybě nebo v dry-run) se vrátí na to, co myčka opravdu má.
 */
function renderSettings(n) {
  if (state.settingPending) return;
  $("set-sound").checked = n.zvuk;
  $("set-last").checked = n.posledni_cyklus;
  $("set-hardness").value = String(n.tvrdost);
}

/** Odešle jedno nastavení a pak načte skutečný stav. */
async function sendSetting(body) {
  state.settingPending = true;
  try {
    const res = await apiPost("/nastaveni", body);
    showResult($("settings-result"), describeCommand(res));
  } catch (err) {
    showResult($("settings-result"), err.message, true);
  } finally {
    state.settingPending = false;
    loadStatus();
  }
}

/* ---------- údržba ---------- */

/** „za N cyklů“ / „po termínu o N cyklů“. */
function describeRemaining(n) {
  return n >= 0 ? `za ${n} cyklů` : `po termínu o ${-n} cyklů`;
}

/** Vykreslí počítadla údržby a historii cyklů. */
function renderMaintenance(m) {
  const put = (id, n, last) => {
    $(id).textContent = describeRemaining(n);
    $(id).classList.toggle("overdue", n <= 0);
    $(`${id}-last`).textContent = last ? `naposledy ${formatTime(last, true)}` : "zatím nezaznamenáno";
  };
  put("m-filter", m.filtr_zbyva, m.filtr_posledni);
  put("m-descale", m.odvapneni_zbyva, m.odvapneni_posledni);

  $("history-empty").hidden = m.historie.length > 0;
  $("history").replaceChildren(...m.historie.map((c) => {
    const tr = el("tr");
    const program = state.programs.find((p) => p.kod === c.program);
    tr.append(el("td", formatTime(c.start, true)), el("td", program ? program.nazev : c.program),
      el("td", optionNames(c.program, c.volby) || "–"), el("td", formatMinutes(c.delka_min)),
      el("td", c.vysledek === "dokonceno" ? "dokončeno" : "zrušeno"));
    return tr;
  }));
}

/** Načte údržbu; dokud server nemá stav myčky, tiše počká na další pokus. */
async function loadMaintenance() {
  try {
    renderMaintenance(await apiGet("/udrzba"));
  } catch {
    /* 503 před prvním čtením myčky – další pokus za MAINT_REFRESH_MS */
  }
}

/** Zapíše provedenou údržbu. */
async function markMaintenance(kind) {
  const label = kind === "filtr" ? "čištění filtru" : "odvápnění";
  if (!confirm(`Zapsat ${label} teď?`)) return;
  try {
    renderMaintenance(await apiPost("/udrzba", { druh: kind }));
  } catch (err) {
    alert(err.message);
  }
}

/* ---------- start stránky ---------- */

/** Načte katalog, napojí ovládání a spustí pravidelné obnovování. */
async function init() {
  try {
    state.programs = await apiGet("/programy");
  } catch (err) {
    $("st-error").hidden = false;
    $("st-error").textContent = err.message;
    return;
  }
  renderPrograms();
  $("options").append(el("span", "Nejdřív vyberte program.", "muted"));
  updatePreview();

  $("btn-start").addEventListener("click", startProgram);
  $("btn-stop").addEventListener("click", stopProgram);
  $("end-time").addEventListener("input", updatePreview);
  for (const r of document.querySelectorAll("input[name=timing]")) r.addEventListener("change", updatePreview);
  $("set-sound").addEventListener("change", (e) => sendSetting({ zvuk: e.target.checked }));
  $("set-last").addEventListener("change", (e) => sendSetting({ posledni_cyklus: e.target.checked }));
  $("set-hardness").addEventListener("change", (e) => sendSetting({ tvrdost: Number(e.target.value) }));
  for (const b of document.querySelectorAll("[data-mark]")) {
    b.addEventListener("click", () => markMaintenance(b.dataset.mark));
  }

  await loadStatus();
  loadMaintenance();
  setInterval(loadStatus, STATUS_REFRESH_MS);
  setInterval(loadMaintenance, MAINT_REFRESH_MS);
}

init();
