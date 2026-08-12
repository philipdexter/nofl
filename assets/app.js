const TEAMS = {
  ARI: { city: "Arizona", name: "Cardinals", color: "#97233f", secondary: "#ffb612" },
  ATL: { city: "Atlanta", name: "Falcons", color: "#a71930", secondary: "#a5acaf" },
  BAL: { city: "Baltimore", name: "Ravens", color: "#241773", secondary: "#9e7c0c" },
  BUF: { city: "Buffalo", name: "Bills", color: "#00338d", secondary: "#c60c30" },
  CAR: { city: "Carolina", name: "Panthers", color: "#0085ca", secondary: "#bfc0bf" },
  CHI: { city: "Chicago", name: "Bears", color: "#0b162a", secondary: "#c83803" },
  CIN: { city: "Cincinnati", name: "Bengals", color: "#fb4f14", secondary: "#f2f2f2" },
  CLE: { city: "Cleveland", name: "Browns", color: "#311d00", secondary: "#ff3c00" },
  DAL: { city: "Dallas", name: "Cowboys", color: "#003594", secondary: "#869397" },
  DEN: { city: "Denver", name: "Broncos", color: "#fb4f14", secondary: "#002244" },
  DET: { city: "Detroit", name: "Lions", color: "#0076b6", secondary: "#b0b7bc" },
  GB: { city: "Green Bay", name: "Packers", color: "#203731", secondary: "#ffb612" },
  HOU: { city: "Houston", name: "Texans", color: "#03202f", secondary: "#a71930" },
  IND: { city: "Indianapolis", name: "Colts", color: "#002c5f", secondary: "#a2aaad" },
  JAX: { city: "Jacksonville", name: "Jaguars", color: "#006778", secondary: "#d7a22a" },
  KC: { city: "Kansas City", name: "Chiefs", color: "#e31837", secondary: "#ffb81c" },
  LV: { city: "Las Vegas", name: "Raiders", color: "#000000", secondary: "#a5acaf" },
  LAC: { city: "Los Angeles", name: "Chargers", color: "#0080c6", secondary: "#ffc20e" },
  LAR: { city: "Los Angeles", name: "Rams", color: "#003594", secondary: "#ffd100" },
  MIA: { city: "Miami", name: "Dolphins", color: "#008e97", secondary: "#fc4c02" },
  MIN: { city: "Minnesota", name: "Vikings", color: "#4f2683", secondary: "#ffc62f" },
  NE: { city: "New England", name: "Patriots", color: "#002244", secondary: "#c60c30" },
  NO: { city: "New Orleans", name: "Saints", color: "#101820", secondary: "#d3bc8d" },
  NYG: { city: "New York", name: "Giants", color: "#0b2265", secondary: "#a71930" },
  NYJ: { city: "New York", name: "Jets", color: "#125740", secondary: "#ffffff" },
  PHI: { city: "Philadelphia", name: "Eagles", color: "#004c54", secondary: "#a5acaf" },
  PIT: { city: "Pittsburgh", name: "Steelers", color: "#101820", secondary: "#ffb612" },
  SEA: { city: "Seattle", name: "Seahawks", color: "#002244", secondary: "#69be28" },
  SF: { city: "San Francisco", name: "49ers", color: "#aa0000", secondary: "#b3995d" },
  TB: { city: "Tampa Bay", name: "Buccaneers", color: "#d50a0a", secondary: "#b1babf" },
  TEN: { city: "Tennessee", name: "Titans", color: "#0c2340", secondary: "#4b92db" },
  WSH: { city: "Washington", name: "Commanders", color: "#5a1414", secondary: "#ffb612" },
};

const STORAGE_KEY = "nofl-preferences-v1";
const elements = {
  teamSelect: document.querySelector("#team-select"),
  timezoneSelect: document.querySelector("#timezone-select"),
  viewButtons: [...document.querySelectorAll("[data-view]")],
  densityButton: document.querySelector("#density-button"),
  shareButton: document.querySelector("#share-button"),
  previousWeek: document.querySelector("#previous-week"),
  nextWeek: document.querySelector("#next-week"),
  weekTrack: document.querySelector("#week-track"),
  weekRange: document.querySelector("#week-range"),
  scheduleHeading: document.querySelector("#schedule-heading"),
  gameCount: document.querySelector("#game-count"),
  scheduleList: document.querySelector("#schedule-list"),
  spotlight: document.querySelector("#team-spotlight"),
  spotlightContent: document.querySelector("#spotlight-content"),
  gameTemplate: document.querySelector("#game-template"),
  toast: document.querySelector("#toast"),
};

let schedule = [];
let state = {
  team: "ALL",
  week: 1,
  view: "all",
  timezone: "local",
  compact: false,
};

function loadPreferences() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state = { ...state, ...stored };
  } catch {
    // A broken preference should never break the schedule.
  }

  const query = new URLSearchParams(window.location.search);
  if (query.has("team") && (query.get("team") === "ALL" || TEAMS[query.get("team")])) {
    state.team = query.get("team");
  }
  if (query.has("week")) state.week = clamp(Number(query.get("week")), 1, 18);
  if (["all", "team", "primetime", "international"].includes(query.get("view"))) {
    state.view = query.get("view");
  }
  if (["local", "America/New_York"].includes(query.get("tz"))) state.timezone = query.get("tz");
  if (query.get("compact") === "1") state.compact = true;
}

function savePreferences() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function clamp(value, min, max) {
  return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : min;
}

function getTimeZone() {
  return state.timezone === "local" ? Intl.DateTimeFormat().resolvedOptions().timeZone : state.timezone;
}

function getCurrentWeek() {
  const now = new Date();
  const futureGames = schedule.filter((game) => game.kickoff && new Date(game.kickoff) >= now);
  if (futureGames.length) return futureGames[0].week;
  return schedule.length ? 18 : 1;
}

function populateTeamSelect() {
  Object.entries(TEAMS)
    .sort(([, a], [, b]) => `${a.city} ${a.name}`.localeCompare(`${b.city} ${b.name}`))
    .forEach(([code, team]) => {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = `${team.city} ${team.name}`;
      elements.teamSelect.append(option);
    });
}

function buildWeekNavigation() {
  const fragment = document.createDocumentFragment();
  for (let week = 1; week <= 18; week += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "week-button";
    button.dataset.week = String(week);
    button.textContent = `W${week}`;
    button.setAttribute("aria-label", `Week ${week}`);
    button.addEventListener("click", () => setWeek(week));
    fragment.append(button);
  }
  elements.weekTrack.append(fragment);
}

function setWeek(week) {
  state.week = clamp(week, 1, 18);
  savePreferences();
  render();
  const active = elements.weekTrack.querySelector(`[data-week="${state.week}"]`);
  active?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
}

function setTeam(code) {
  state.team = TEAMS[code] ? code : "ALL";
  elements.teamSelect.value = state.team;
  savePreferences();
  render();
}

function isPrimeTime(game) {
  if (!game.kickoff) return false;
  const easternHour = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York",
      hour: "2-digit",
      hourCycle: "h23",
    }).format(new Date(game.kickoff)),
  );
  return easternHour >= 19;
}

function filteredGames() {
  const games = schedule.filter((game) => game.week === state.week);
  if (state.view === "team") {
    if (state.team === "ALL") return games;
    return games.filter((game) => game.away === state.team || game.home === state.team);
  }
  if (state.view === "primetime") return games.filter(isPrimeTime);
  if (state.view === "international") return games.filter((game) => game.neutralSite);
  return games;
}

function formatDateParts(kickoff) {
  if (!kickoff) return { key: "tbd", day: "Date & time", date: "To be announced" };
  const date = new Date(kickoff);
  const timeZone = getTimeZone();
  return {
    key: new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(date),
    day: new Intl.DateTimeFormat("en-US", { timeZone, weekday: "long" }).format(date),
    date: new Intl.DateTimeFormat("en-US", { timeZone, month: "short", day: "numeric" }).format(date),
  };
}

function formatKickoff(kickoff) {
  if (!kickoff) return { time: "TBD", zone: "Schedule flex" };
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: getTimeZone(),
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
  const parts = formatter.formatToParts(new Date(kickoff));
  const zone = parts.find((part) => part.type === "timeZoneName")?.value || "";
  const time = parts
    .filter((part) => !["timeZoneName", "literal"].includes(part.type) || part.value.trim() === ":")
    .map((part) => part.value)
    .join("")
    .trim();
  return { time, zone };
}

function weekRange(games) {
  const datedGames = games.filter((game) => game.kickoff);
  if (!datedGames.length) return "Dates and kickoff times to be announced";
  const first = new Date(datedGames[0].kickoff);
  const last = new Date(datedGames.at(-1).kickoff);
  const timeZone = getTimeZone();
  const firstLabel = new Intl.DateTimeFormat("en-US", { timeZone, month: "long", day: "numeric" }).format(first);
  const lastLabel = new Intl.DateTimeFormat("en-US", { timeZone, month: "long", day: "numeric" }).format(last);
  return firstLabel === lastLabel ? firstLabel : `${firstLabel} — ${lastLabel}`;
}

function makeTeam(teamElement, code, side) {
  const team = TEAMS[code];
  teamElement.dataset.team = code;
  teamElement.setAttribute("aria-label", `Follow the ${team.city} ${team.name}`);
  teamElement.querySelector(`.${side}-token`).textContent = code;
  teamElement.querySelector(`.${side}-token`).style.setProperty("--team-color", team.color);
  teamElement.querySelector(`.${side}-token`).style.setProperty("--team-secondary", team.secondary);
  teamElement.querySelector(`.${side}-city`).textContent = team.city;
  teamElement.querySelector(`.${side}-name`).textContent = team.name;
  teamElement.addEventListener("click", () => {
    setTeam(code);
    showToast(`Following ${team.city} ${team.name}`);
  });
}

function buildGameCard(game) {
  const card = elements.gameTemplate.content.firstElementChild.cloneNode(true);
  const selected = state.team !== "ALL" && (game.away === state.team || game.home === state.team);
  const kickoff = formatKickoff(game.kickoff);
  card.dataset.gameId = game.id;
  card.querySelector(".time-value").textContent = kickoff.time;
  card.querySelector(".time-zone").textContent = kickoff.zone;
  makeTeam(card.querySelector(".away-team"), game.away, "away");
  makeTeam(card.querySelector(".home-team"), game.home, "home");
  card.querySelector(".network").textContent = game.broadcast;
  card.querySelector(".venue").textContent = [game.venue, game.location].filter(Boolean).join(" · ");
  card.querySelector(".game-note").textContent = game.note || (game.neutralSite ? "International game" : "");

  if (selected) {
    card.classList.add("is-followed");
    card.style.setProperty("--team-accent", TEAMS[state.team].color);
  } else if (state.team !== "ALL" && state.view === "all") {
    card.classList.add("is-dimmed");
  }

  const calendarButton = card.querySelector(".calendar-button");
  if (!game.kickoff) {
    calendarButton.disabled = true;
    calendarButton.title = "Calendar export will be available when kickoff is announced";
  } else {
    calendarButton.addEventListener("click", () => downloadCalendar(game));
  }
  return card;
}

function renderSchedule() {
  const allWeekGames = schedule.filter((game) => game.week === state.week);
  const games = filteredGames();
  elements.scheduleHeading.textContent = `Week ${state.week}`;
  elements.weekRange.textContent = weekRange(allWeekGames);
  elements.gameCount.textContent = `${games.length} ${games.length === 1 ? "game" : "games"}`;
  elements.scheduleList.replaceChildren();

  if (!games.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = "<h3>Nothing on this channel.</h3><p>Try another week or switch back to all games.</p>";
    elements.scheduleList.append(empty);
    elements.scheduleList.setAttribute("aria-busy", "false");
    return;
  }

  const groups = new Map();
  games.forEach((game) => {
    const date = formatDateParts(game.kickoff);
    if (!groups.has(date.key)) groups.set(date.key, { ...date, games: [] });
    groups.get(date.key).games.push(game);
  });

  groups.forEach((group) => {
    const section = document.createElement("section");
    section.className = "date-group";
    const heading = document.createElement("h3");
    heading.className = "date-heading";
    heading.append(document.createTextNode(group.day));
    const subheading = document.createElement("span");
    subheading.textContent = group.date;
    heading.append(subheading);
    const cardList = document.createElement("div");
    cardList.className = "date-games";
    group.games.forEach((game) => cardList.append(buildGameCard(game)));
    section.append(heading, cardList);
    elements.scheduleList.append(section);
  });
  elements.scheduleList.setAttribute("aria-busy", "false");
}

function renderSpotlight() {
  if (state.team === "ALL") {
    elements.spotlight.removeAttribute("data-color");
    elements.spotlight.style.removeProperty("--spotlight-color");
    elements.spotlightContent.innerHTML = '<p class="spotlight-empty">Choose a team to make this schedule yours.</p>';
    return;
  }

  const now = new Date();
  const team = TEAMS[state.team];
  const teamGames = schedule.filter((game) => game.away === state.team || game.home === state.team);
  const game = teamGames.find((candidate) => candidate.kickoff && new Date(candidate.kickoff) >= now) || teamGames[0];
  elements.spotlight.dataset.color = state.team;
  elements.spotlight.style.setProperty("--spotlight-color", team.color);
  elements.spotlightContent.replaceChildren();
  const wrapper = document.createElement("div");
  wrapper.className = "spotlight-matchup";
  const opponentCode = game.away === state.team ? game.home : game.away;
  const opponent = TEAMS[opponentCode];
  const homeAway = game.home === state.team ? "vs." : "at";
  const title = document.createElement("strong");
  title.textContent = `${team.name} ${homeAway} ${opponent.name}`;
  const detail = document.createElement("p");
  const date = game.kickoff
    ? new Intl.DateTimeFormat("en-US", { timeZone: getTimeZone(), weekday: "long", month: "long", day: "numeric" }).format(new Date(game.kickoff))
    : "Date to be announced";
  detail.textContent = `Week ${game.week} · ${date} · ${formatKickoff(game.kickoff).time}`;
  wrapper.append(title, detail);
  elements.spotlightContent.append(wrapper);
}

function renderControls() {
  elements.teamSelect.value = state.team;
  elements.timezoneSelect.value = state.timezone;
  elements.viewButtons.forEach((button) => {
    const active = button.dataset.view === state.view;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  elements.densityButton.setAttribute("aria-pressed", String(state.compact));
  document.body.classList.toggle("is-compact", state.compact);
  elements.previousWeek.disabled = state.week === 1;
  elements.nextWeek.disabled = state.week === 18;
  document.querySelectorAll(".week-button").forEach((button) => {
    const active = Number(button.dataset.week) === state.week;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
}

function render() {
  renderControls();
  renderSchedule();
  renderSpotlight();
}

function escapeICS(value) {
  return value.replaceAll("\\", "\\\\").replaceAll(",", "\\,").replaceAll(";", "\\;").replaceAll("\n", "\\n");
}

function toICSDate(date) {
  return date.toISOString().replaceAll(/[-:]/g, "").replace(".000", "");
}

function downloadCalendar(game) {
  const start = new Date(game.kickoff);
  const end = new Date(start.getTime() + 4 * 60 * 60 * 1000);
  const away = TEAMS[game.away];
  const home = TEAMS[game.home];
  const title = `${away.city} ${away.name} at ${home.city} ${home.name}`;
  const location = [game.venue, game.location].filter(Boolean).join(", ");
  const contents = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//NOFL//Spoiler-free schedule//EN",
    "BEGIN:VEVENT",
    `UID:${game.id}@nofl.local`,
    `DTSTAMP:${toICSDate(new Date())}`,
    `DTSTART:${toICSDate(start)}`,
    `DTEND:${toICSDate(end)}`,
    `SUMMARY:${escapeICS(title)}`,
    `LOCATION:${escapeICS(location)}`,
    `DESCRIPTION:${escapeICS(`Week ${game.week} · ${game.broadcast || "Broadcast TBD"}`)}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([contents], { type: "text/calendar;charset=utf-8" }));
  link.download = `${game.away}-at-${game.home}-week-${game.week}.ics`;
  link.click();
  URL.revokeObjectURL(link.href);
  showToast("Calendar event downloaded");
}

let toastTimer;
function showToast(message) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.add("is-visible");
  toastTimer = setTimeout(() => elements.toast.classList.remove("is-visible"), 2200);
}

async function shareView() {
  const url = new URL(window.location.href);
  url.search = "";
  if (state.team !== "ALL") url.searchParams.set("team", state.team);
  url.searchParams.set("week", String(state.week));
  if (state.view !== "all") url.searchParams.set("view", state.view);
  if (state.timezone !== "local") url.searchParams.set("tz", state.timezone);
  if (state.compact) url.searchParams.set("compact", "1");
  try {
    await navigator.clipboard.writeText(url.toString());
    showToast("View link copied");
  } catch {
    window.history.replaceState({}, "", url);
    showToast("Shareable view added to the address bar");
  }
}

function bindEvents() {
  elements.teamSelect.addEventListener("change", (event) => setTeam(event.target.value));
  elements.timezoneSelect.addEventListener("change", (event) => {
    state.timezone = event.target.value;
    savePreferences();
    render();
  });
  elements.viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.view === "team" && state.team === "ALL") {
        showToast("Choose a team first");
        elements.teamSelect.focus();
        return;
      }
      state.view = button.dataset.view;
      savePreferences();
      render();
    });
  });
  elements.previousWeek.addEventListener("click", () => setWeek(state.week - 1));
  elements.nextWeek.addEventListener("click", () => setWeek(state.week + 1));
  elements.densityButton.addEventListener("click", () => {
    state.compact = !state.compact;
    savePreferences();
    renderControls();
  });
  elements.shareButton.addEventListener("click", shareView);
}

async function init() {
  populateTeamSelect();
  buildWeekNavigation();
  loadPreferences();
  bindEvents();
  try {
    const response = await fetch("data/schedule.json");
    if (!response.ok) throw new Error(`Schedule request failed: ${response.status}`);
    const payload = await response.json();
    schedule = payload.games;
    const hasWeekQuery = new URLSearchParams(window.location.search).has("week");
    const hasStoredWeek = (() => {
      try { return Object.hasOwn(JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"), "week"); }
      catch { return false; }
    })();
    if (!hasWeekQuery && !hasStoredWeek) state.week = getCurrentWeek();
    render();
  } catch (error) {
    console.error(error);
    elements.scheduleList.innerHTML = '<div class="error-card">The schedule could not load. Serve this folder with a local web server and try again.</div>';
    elements.scheduleList.setAttribute("aria-busy", "false");
  }
}

init();
