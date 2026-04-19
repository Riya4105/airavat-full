// app.js — AIRAVAT 3.0 Full Product Frontend

const API = "https://airavat-full.onrender.com";

let map, markers = {}, selectedZone = null;
let sstChart = null, simulationRunning = false;
let allZoneData = [], assignedZones = [];
let authToken = null, currentAgency = null, cachedBaselines = null;
const zoneCache = {};

const COLOURS = { HIGH: "#EF4444", WARN: "#F97316", NORMAL: "#6B7280" };

const ZONE_CENTRES = {
  Z1: [20.0, 60.0], Z2: [24.5, 60.5], Z3: [11.5, 74.5],
  Z4: [18.5, 86.0], Z5: [8.5, 81.5],  Z6: [11.5, 76.0], Z7: [12.0, 97.0]
};

function prefetchZone(zoneId) {
  if (zoneCache[zoneId]) return;
  fetch(`${API}/history/${zoneId}?days=30`)
    .then(r => r.json())
    .then(data => { zoneCache[zoneId] = data; })
    .catch(() => {});
}

function fillLogin(user, pass) {
  document.getElementById("login-username").value = user;
  document.getElementById("login-password").value = pass;
}

async function doLogin() {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errEl = document.getElementById("login-error");
  const btn = document.getElementById("login-btn");

  if (!username || !password) {
    errEl.textContent = "Please enter agency ID and password";
    return;
  }

  btn.textContent = "Connecting...";
  btn.disabled = true;
  errEl.textContent = "";

  fetch(`${API}/baseline`)
    .then(r => r.json())
    .then(data => { cachedBaselines = data; })
    .catch(() => {});

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }

    const data = await res.json();
    authToken = data.access_token;
    currentAgency = { name: data.agency, zones: data.zones, role: data.role };
    assignedZones = data.zones;

    document.getElementById("agency-badge").textContent =
      `${currentAgency.name} · ${currentAgency.role.toUpperCase()}`;
    document.getElementById("footer-agency").textContent = currentAgency.name;
    document.getElementById("footer-role").textContent = currentAgency.role.toUpperCase();

    document.getElementById("login-screen").style.display = "none";
    const app = document.getElementById("app");
    app.style.display = "flex";

    initMap();
    loadZones();
    loadFeedbackStats();
    setInterval(loadZones, 30000);
    setInterval(loadFeedbackStats, 30000);

  } catch (e) {
    errEl.textContent = e.message || "Login failed — check credentials";
    btn.textContent = "Access Sentinel";
    btn.disabled = false;
  }
}

function doLogout() {
  authToken = null;
  currentAgency = null;
  assignedZones = [];
  allZoneData = [];
  selectedZone = null;
  cachedBaselines = null;
  Object.keys(zoneCache).forEach(k => delete zoneCache[k]);

  if (map) {
    Object.values(markers).forEach(m => map.removeLayer(m));
    markers = {};
    map.remove();
    map = null;
  }

  if (sstChart) { sstChart.destroy(); sstChart = null; }

  document.getElementById("zone-list").innerHTML = "Loading...";
  document.getElementById("detail-placeholder").style.display = "block";
  document.getElementById("detail-content").style.display = "none";
  document.getElementById("chat-messages").innerHTML = "Ask about any zone...";
  document.getElementById("tp").textContent = "0";
  document.getElementById("fp").textContent = "0";
  document.getElementById("acc").textContent = "—";

  document.getElementById("login-screen").style.display = "flex";
  document.getElementById("app").style.display = "none";
  document.getElementById("login-username").value = "";
  document.getElementById("login-password").value = "";
  document.getElementById("login-error").textContent = "";
  document.getElementById("login-btn").textContent = "Access Sentinel";
  document.getElementById("login-btn").disabled = false;
}

function initMap() {
  map = L.map("map", { center: [15, 75], zoom: 5 });
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "© CARTO © OpenStreetMap", maxZoom: 18
  }).addTo(map);
}

function makeIcon(alertLevel, chainPos, chainTotal) {
  const col = COLOURS[alertLevel] || COLOURS.NORMAL;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44">
    <circle cx="22" cy="22" r="19" fill="none" stroke="${col}" stroke-width="2.5" opacity="0.35"/>
    <circle cx="22" cy="22" r="13" fill="none" stroke="${col}" stroke-width="2"/>
    <text x="22" y="27" text-anchor="middle" font-size="11" font-weight="700" font-family="monospace" fill="${col}">${chainPos}/${chainTotal}</text>
    </svg>`;
  return L.divIcon({ html: svg, className: "", iconSize: [44, 44], iconAnchor: [22, 22] });
}

async function loadZones() {
  try {
    const res = await fetch(`${API}/zones`);
    const data = await res.json();
    allZoneData = data.zones.filter(z => assignedZones.includes(z.zone_id));
    document.getElementById("last-updated").textContent = new Date().toLocaleTimeString();

    allZoneData.forEach(z => {
      const pos = ZONE_CENTRES[z.zone_id];
      if (!pos) return;
      const icon = makeIcon(z.alert_level, z.chain_position, z.chain_total);
      if (markers[z.zone_id]) {
        markers[z.zone_id].setIcon(icon);
      } else {
        const m = L.marker(pos, { icon }).addTo(map);
        m.on("click", () => selectZone(z.zone_id));
        markers[z.zone_id] = m;
      }
    });

    renderLeaderboard(allZoneData);
    if (selectedZone) selectZone(selectedZone);
  } catch (e) { console.error("Failed to load zones:", e); }
}

function renderLeaderboard(zones) {
  document.getElementById("zone-list").innerHTML = zones.map((z, i) => `
    <div class="zone-row ${selectedZone === z.zone_id ? 'selected' : ''}"
         onclick="selectZone('${z.zone_id}')"
         onmouseenter="prefetchZone('${z.zone_id}')">
      <span class="zone-rank">${i + 1}</span>
      <span class="dot ${z.alert_level.toLowerCase()}"></span>
      <span class="zone-name-label">${z.zone_name}</span>
      <span class="zone-score score-${z.alert_level}">${z.priority}</span>
    </div>`).join("");
}

async function selectZone(zoneId) {
  selectedZone = zoneId;
  renderLeaderboard(allZoneData);
  try {
    const res = await fetch(`${API}/zones/${zoneId}`);
    const z = await res.json();

    document.getElementById("detail-placeholder").style.display = "none";
    document.getElementById("detail-content").style.display = "block";
    document.getElementById("detail-name").textContent = z.zone_name;
    const badge = document.getElementById("detail-badge");
    badge.textContent = z.alert_level;
    badge.className = `alert-badge ${z.alert_level}`;
    document.getElementById("detail-event").textContent = z.best_match.replace(/_/g, " ");

    const dots = document.getElementById("chain-dots");
    dots.innerHTML = "";
    for (let i = 0; i < z.chain_total; i++) {
      const d = document.createElement("div");
      d.className = "chain-dot" +
        (i < z.chain_position - 1 ? " active" : "") +
        (i === z.chain_position - 1 ? " current" : "");
      dots.appendChild(d);
    }
    document.getElementById("chain-desc").textContent = z.chain_description;

    const pct = Math.round(z.confidence * 100);
    document.getElementById("conf-bar").style.width = `${pct}%`;
    document.getElementById("conf-label").textContent = `${pct}% convergence confidence`;

    if (!cachedBaselines) {
      cachedBaselines = await fetch(`${API}/baseline`).then(r => r.json());
    }
    const b = cachedBaselines.baselines.find(b => b.zone_id === zoneId);
    const delta = b ? (z.latest_sst - b.mean_sst).toFixed(2) : "0";
    document.getElementById("sst-delta").textContent = `${delta > 0 ? "+" : ""}${delta}C`;
    document.getElementById("trajectory").innerHTML = z.slope_score > 0.5
      ? '<span style="color:#EF4444">Rising</span>'
      : '<span style="color:#60A5FA">Stable</span>';
    document.getElementById("priority-val").textContent = `${Math.round(z.priority * 100)} / 100`;
    document.getElementById("event-type").textContent = z.best_match.replace(/_/g, " ");

    // VAE anomaly score
    const vaeEl = document.getElementById("vae-anomaly");
    if (vaeEl && z.vae_anomaly !== undefined) {
      vaeEl.textContent = `${Math.round(z.vae_anomaly * 100)}%`;
      vaeEl.style.color = z.vae_anomaly > 0.7 ? "#EF4444"
                        : z.vae_anomaly > 0.4 ? "#F97316" : "#1D9E75";
    }

    // Observation count
    const obsEl = document.getElementById("obs-count");
    if (obsEl) obsEl.textContent = `${z.obs_count} days`;

    const actions = {
      thermal_stress:  "URGENT: Thermal stress detected. Dispatch response team.",
      hypoxic_bloom:   "Monitor closely. Hypoxic bloom forming. Increase sampling.",
      turbidity_spike: "Investigate turbidity source. Check for runoff.",
      upwelling:       "Upwelling in progress. High productivity zone.",
      oil_slick:       "Oil slick precursor. Alert coast guard immediately.",
      normal:          "Zone within normal parameters. Routine monitoring."
    };
    document.getElementById("rec-action").textContent = actions[z.best_match] || "Monitor zone.";

    const chartEl = document.getElementById("sst-chart");
    chartEl.style.opacity = "0.3";
    renderSSTChart(zoneId).then(() => { chartEl.style.opacity = "1"; });

  } catch (e) { console.error("Zone detail error:", e); }
}

async function renderSSTChart(zoneId) {
  try {
    let data;
    if (zoneCache[zoneId]) {
      data = zoneCache[zoneId];
    } else {
      const res = await fetch(`${API}/history/${zoneId}?days=30`);
      data = await res.json();
      zoneCache[zoneId] = data;
    }
    const obs = data.observations;
    const labels = obs.map(o => o.time.slice(5, 10));
    const sst = obs.map(o => o.sst);
    if (sstChart) sstChart.destroy();
    const ctx = document.getElementById("sst-chart").getContext("2d");
    sstChart = new Chart(ctx, {
      type: "line",
      data: { labels, datasets: [{ data: sst, borderColor: "#EF4444",
        backgroundColor: "rgba(239,68,68,0.08)", borderWidth: 1.5,
        pointRadius: 2, tension: 0.3, fill: true }] },
      options: { responsive: true, plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8B949E", font: { size: 9 } }, grid: { color: "#21262D" } },
          y: { ticks: { color: "#8B949E", font: { size: 9 } }, grid: { color: "#21262D" } }
        }}
    });
  } catch (e) { console.error("Chart error:", e); }
}

async function sendFeedback(type) {
  if (!selectedZone) return;
  const z = allZoneData.find(z => z.zone_id === selectedZone);
  if (!z) return;
  await fetch(`${API}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ zone_id: selectedZone, alert_level: z.alert_level, event_type: z.best_match, feedback: type })
  });
  loadFeedbackStats();
  addChatMessage("system", type === "confirm" ? "Confirmed - chain reinforced" : "Logged as false positive");
}

async function loadFeedbackStats() {
  try {
    const res = await fetch(`${API}/feedback`);
    const data = await res.json();
    document.getElementById("tp").textContent = data.true_positives;
    document.getElementById("fp").textContent = data.false_positives;
    document.getElementById("acc").textContent = data.total > 0 ? `${Math.round(data.accuracy * 100)}%` : "-";
  } catch (e) {}
}

async function sendQuery() {
  const input = document.getElementById("chat-input");
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  addChatMessage("user", q);
  try {
    const res = await fetch(`${API}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, zone_id: selectedZone })
    });
    const data = await res.json();
    const reply = [
      data.severity ? `Severity: ${data.severity}` : "",
      data.chain_state ? `Chain: ${data.chain_state}` : "",
      data.explanation || "",
      data.action ? `Action: ${data.action}` : ""
    ].filter(Boolean).join(" | ");
    addChatMessage("ai", reply);
  } catch (e) { addChatMessage("ai", "Error connecting to AIRAVAT."); }
}

function addChatMessage(role, text) {
  const box = document.getElementById("chat-messages");
  const col = role === "user" ? "#9FE1CB" : "#E6EDF3";
  box.innerHTML += `<div style="color:${col};margin-bottom:4px;">${text}</div>`;
  box.scrollTop = box.scrollHeight;
}

function toggleSimulate() {
  const btn = document.getElementById("simulate-btn");
  if (simulationRunning) {
    simulationRunning = false;
    btn.textContent = "Simulate 8-day progression";
    btn.classList.remove("running");
    loadZones();
    return;
  }
  simulationRunning = true;
  btn.textContent = "Stop simulation";
  btn.classList.add("running");
  let step = 0;
  const sim = setInterval(() => {
    if (!simulationRunning || step >= 8) {
      clearInterval(sim);
      simulationRunning = false;
      btn.textContent = "Simulate 8-day progression";
      btn.classList.remove("running");
      loadZones();
      return;
    }
    allZoneData = allZoneData.map(z => ({
      ...z,
      chain_position: Math.min(z.chain_position + 1, z.chain_total),
      priority: Math.min(z.priority + 0.04, 1.0),
      alert_level: z.priority + 0.04 >= 0.55 ? "HIGH" : z.priority + 0.04 >= 0.35 ? "WARN" : "NORMAL"
    }));
    allZoneData.forEach(z => {
      if (!markers[z.zone_id]) return;
      markers[z.zone_id].setIcon(makeIcon(z.alert_level, z.chain_position, z.chain_total));
    });
    renderLeaderboard(allZoneData);
    step++;
  }, 1000);
}

// Boot — show login screen first
