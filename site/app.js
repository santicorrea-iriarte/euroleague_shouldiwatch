const LABEL_RANK = { skip: 0, maybe: 1, watch: 2, top: 3 };
const BD_ORDER = ["closeness", "wire", "lead_changes", "clutch", "late_drama", "comeback", "overtime", "star_power", "flow", "context"];

const state = {
  data: null,
  view: localStorage.getItem("view") || "round",
  round: null,
  team: "",
  minLabel: "skip",
  sort: "date",
  spoilers: localStorage.getItem("spoilers") === "1",
  revealed: new Set(),
  open: new Set(),
};

const $ = (s) => document.querySelector(s);
const t = (k, p) => I18N.t(k, p);

function roundKey(g) {
  return `${g.phase}|${g.round}`;
}

function roundName(key) {
  const [phase, r] = key.split("|");
  return phase === "RS" ? `${t("round")} ${r}` : `${t("phase_" + phase)} · ${r}`;
}

function tagText(tag) {
  const p = tag.p || {};
  if (tag.k === "overtime") return p.n > 1 ? t("tag_overtime_n", p) : t("tag_overtime_1");
  if (tag.k === "phase") return t("phase_" + p.phase);
  return t("tag_" + tag.k, p);
}

function fmtDate(iso) {
  return new Intl.DateTimeFormat(I18N.lang, {
    weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  }).format(new Date(iso));
}

function populateControls() {
  const games = state.data.games;
  const keys = [...new Set(games.map(roundKey))].sort((a, b) => {
    const ga = games.find((g) => roundKey(g) === a), gb = games.find((g) => roundKey(g) === b);
    return ga.date.localeCompare(gb.date);
  });
  state.rounds = keys;
  if (!state.round || !keys.includes(state.round)) state.round = keys[keys.length - 1];
  $("#round").innerHTML = keys.map((k) => `<option value="${k}">${roundName(k)}</option>`).join("");
  $("#round").value = state.round;

  const teams = new Map();
  games.forEach((g) => [g.home, g.away].forEach((c) => teams.set(c.code, c.name)));
  const sorted = [...teams].sort((a, b) => a[1].localeCompare(b[1]));
  $("#team").innerHTML = `<option value="">${t("all_teams")}</option>` +
    sorted.map(([c, n]) => `<option value="${c}">${n}</option>`).join("");
  $("#team").value = state.team;
}

function visibleGames() {
  let gs = state.data.games.filter((g) =>
    LABEL_RANK[g.label] >= LABEL_RANK[state.minLabel] &&
    (!state.team || g.home.code === state.team || g.away.code === state.team));
  if (state.view === "round") {
    gs = gs.filter((g) => roundKey(g) === state.round);
    gs.sort(state.sort === "score" ? (a, b) => b.uncapped - a.uncapped : (a, b) => a.date.localeCompare(b.date));
  } else {
    gs.sort((a, b) => b.uncapped - a.uncapped);
    gs = gs.slice(0, 50);
  }
  return gs;
}

function renderDetails(g, el) {
  const tags = g.tags.length
    ? `<ul class="tags">${g.tags.map((x) => `<li>${tagText(x)}</li>`).join("")}</ul>`
    : `<p class="muted">${t("no_tags")}</p>`;
  const max = 40;
  const rows = BD_ORDER.filter((k) => g.breakdown[k]).map((k) => {
    const v = g.breakdown[k];
    const w = Math.min(100, (Math.abs(v) / max) * 100);
    return `<div class="bd-row"><span>${t("bd_" + k)}</span>
      <span class="bar"><i class="${v < 0 ? "neg" : ""}" style="width:${w}%"></i></span>
      <b>${v > 0 ? "+" : ""}${v}</b></div>`;
  }).join("");
  el.innerHTML = `${tags}
    <h4>${t("breakdown")}</h4>${rows}
    <div class="bd-row total"><span>${t("uncapped")}</span><span></span><b>${g.uncapped}</b></div>
    ${g.partial ? `<p class="muted small">${t("partial")}</p>` : ""}`;
}

function render() {
  document.querySelectorAll("[data-view]").forEach((b) => b.setAttribute("aria-selected", b.dataset.view === state.view));
  $("#roundNav").hidden = state.view !== "round";
  $("#sort").hidden = state.view !== "round";
  const i = state.rounds.indexOf(state.round);
  $("#prevRound").disabled = i <= 0;
  $("#nextRound").disabled = i >= state.rounds.length - 1;

  const box = $("#games");
  box.innerHTML = "";
  const gs = visibleGames();
  if (!gs.length) box.innerHTML = `<p class="empty">${t("empty")}</p>`;
  const tpl = $("#cardTpl");
  gs.forEach((g, idx) => {
    const c = tpl.content.firstElementChild.cloneNode(true);
    c.classList.add(`l-${g.label}`);
    c.querySelector(".when").textContent =
      (state.view === "best" ? `#${idx + 1} · ${roundName(roundKey(g))} · ` : "") + fmtDate(g.date);
    for (const side of ["home", "away"]) {
      const el = c.querySelector(`.team.${side}`);
      el.querySelector("span").textContent = g[side].name;
      if (g[side].crest) el.querySelector("img").src = g[side].crest;
      else el.querySelector("img").remove();
    }
    c.querySelector(".num").textContent = g.score;
    c.querySelector(".ring").style.setProperty("--p", g.score);
    c.querySelector(".label").textContent = t("label_" + g.label);

    const shown = state.spoilers || state.revealed.has(g.id);
    const res = c.querySelector(".result");
    res.hidden = !shown;
    res.innerHTML = `<span>${g.home.name}</span><b>${g.result[0]} – ${g.result[1]}</b><span>${g.away.name}</span>`;
    const rb = c.querySelector(".reveal-btn");
    rb.textContent = shown ? t("hide_result") : t("reveal");
    rb.hidden = state.spoilers;
    rb.onclick = () => {
      state.revealed.has(g.id) ? state.revealed.delete(g.id) : state.revealed.add(g.id);
      render();
    };

    const open = state.open.has(g.id);
    const db = c.querySelector(".details-btn");
    db.innerHTML = open ? t("hide_details") : `${t("details")} <small>(${t("details_hint")})</small>`;
    db.setAttribute("aria-expanded", open);
    const det = c.querySelector(".details");
    det.hidden = !open;
    if (open) renderDetails(g, det);
    db.onclick = () => {
      state.open.has(g.id) ? state.open.delete(g.id) : state.open.add(g.id);
      render();
    };
    box.appendChild(c);
  });

  const upd = new Intl.DateTimeFormat(I18N.lang, { dateStyle: "medium", timeStyle: "short" })
    .format(new Date(state.data.generated));
  $("#meta").textContent = `${state.data.name} · ${state.data.games.length} ${t("games")} · ${t("updated")}: ${upd}`;
}

function bind() {
  document.querySelectorAll("[data-view]").forEach((b) => (b.onclick = () => {
    state.view = b.dataset.view;
    localStorage.setItem("view", state.view);
    render();
  }));
  $("#round").onchange = (e) => { state.round = e.target.value; render(); };
  $("#prevRound").onclick = () => { state.round = state.rounds[state.rounds.indexOf(state.round) - 1]; $("#round").value = state.round; render(); };
  $("#nextRound").onclick = () => { state.round = state.rounds[state.rounds.indexOf(state.round) + 1]; $("#round").value = state.round; render(); };
  $("#team").onchange = (e) => { state.team = e.target.value; render(); };
  $("#minLabel").onchange = (e) => { state.minLabel = e.target.value; render(); };
  $("#sort").onchange = (e) => { state.sort = e.target.value; render(); };
  $("#spoilers").checked = state.spoilers;
  $("#spoilers").onchange = (e) => {
    state.spoilers = e.target.checked;
    localStorage.setItem("spoilers", state.spoilers ? "1" : "0");
    render();
  };
  $("#lang").onclick = async () => { await I18N.toggle(); populateControls(); render(); };
}

(async function init() {
  await I18N.load(I18N.lang);
  const seasons = await (await fetch("data/seasons.json")).json();
  state.data = await (await fetch(`data/games-${seasons[0].code}.json`)).json();
  populateControls();
  bind();
  render();
})();
