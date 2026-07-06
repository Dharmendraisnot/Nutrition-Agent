/* ═══════════════════════════════════════════════════════
   NutriBot — Frontend JavaScript
   IBM Watsonx.ai Nutrition Agent
═══════════════════════════════════════════════════════ */

"use strict";

// ── State ───────────────────────────────────────────────
let currentSection = "hero";
let waterGlasses   = 3;
let memberCount    = 0;

// ── Section Navigation ──────────────────────────────────
function showSection(name) {
  // Hide all
  ["hero", "chat", "dashboard", "mealplan", "bmi", "family"].forEach(s => {
    const el = document.getElementById(s + "Section");
    if (el) el.style.display = "none";
  });

  // Show hero only when explicitly called
  const heroEl = document.getElementById("heroSection");
  if (heroEl) heroEl.style.display = name === "hero" ? "block" : "none";

  // Show target
  const target = document.getElementById(name + "Section");
  if (target) target.style.display = "block";
  currentSection = name;

  // Update nav active state
  document.querySelectorAll(".nav-pill").forEach(a => {
    a.classList.remove("active");
    if (a.getAttribute("onclick") && a.getAttribute("onclick").includes(`'${name}'`)) {
      a.classList.add("active");
    }
  });

  // Section-specific inits
  if (name === "family" && memberCount === 0) {
    addMemberRow();
  }
  if (name === "chat") {
    setTimeout(() => document.getElementById("chatInput").focus(), 100);
  }
}

// ── Dark Mode ───────────────────────────────────────────
function toggleDark() {
  const html = document.documentElement;
  const isDark = html.getAttribute("data-bs-theme") === "dark";
  html.setAttribute("data-bs-theme", isDark ? "light" : "dark");
  const btn = document.getElementById("darkToggle");
  btn.innerHTML = isDark
    ? '<i class="bi bi-moon-stars"></i>'
    : '<i class="bi bi-sun"></i>';
  localStorage.setItem("nutri-theme", isDark ? "light" : "dark");
}

// Restore saved theme
(function restoreTheme() {
  const saved = localStorage.getItem("nutri-theme");
  if (saved === "dark") {
    document.documentElement.setAttribute("data-bs-theme", "dark");
    const btn = document.getElementById("darkToggle");
    if (btn) btn.innerHTML = '<i class="bi bi-sun"></i>';
  }
})();

// ── Markdown → HTML (simple) ────────────────────────────
function markdownToHtml(text) {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^#{1,2}\s+(.+)$/gm, "<h4>$1</h4>")
    .replace(/^#{3,6}\s+(.+)$/gm, "<h5>$1</h5>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
    .replace(/(<li>[\s\S]*?<\/li>)/g, m => `<ul>${m}</ul>`)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/\n/g, "<br/>")
    .replace(/^(?!<[hup])(.+)$/gm, "<p>$1</p>")
    .replace(/<p><\/p>/g, "")
    // Fix nested ul
    .replace(/(<ul>)+/g, "<ul>").replace(/(<\/ul>)+/g, "</ul>");
}

// ── Chat ────────────────────────────────────────────────
function handleChatKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function sendSuggestion(text) {
  document.getElementById("chatInput").value = text;
  sendMessage();
}

async function sendMessage() {
  const input = document.getElementById("chatInput");
  const msg   = input.value.trim();
  if (!msg) return;

  input.value = "";
  autoResizeTextarea(input);

  // Hide welcome
  const welcome = document.querySelector(".chat-welcome");
  if (welcome) welcome.style.display = "none";

  appendBubble("user", msg);
  const typingId = appendTyping();
  setSendDisabled(true);

  try {
    const res  = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    removeTyping(typingId);
    appendBubble("bot", data.reply || "Sorry, I couldn't respond.");
    if (data.elapsed) {
      console.info(`Watsonx response time: ${data.elapsed}s`);
    }
  } catch (err) {
    removeTyping(typingId);
    appendBubble("bot", "⚠️ Network error. Please check your connection and try again.");
  } finally {
    setSendDisabled(false);
    input.focus();
  }
}

function appendBubble(role, text) {
  const container = document.getElementById("chatMessages");
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isBot = role === "bot";
  const html = `
    <div class="chat-bubble-wrap ${isBot ? "bot" : "user"}">
      ${isBot ? `<div class="chat-avatar bot-av"><i class="bi bi-robot"></i></div>` : ""}
      <div>
        <div class="chat-bubble ${isBot ? "bot-bubble" : "user-bubble"}">${isBot ? markdownToHtml(text) : escHtml(text)}</div>
        <div class="chat-time ${isBot ? "" : "user-wrap"}">${now}</div>
      </div>
      ${!isBot ? `<div class="chat-avatar user-av"><i class="bi bi-person-fill"></i></div>` : ""}
    </div>`;
  container.insertAdjacentHTML("beforeend", html);
  container.scrollTop = container.scrollHeight;
}

function appendTyping() {
  const id = "typing-" + Date.now();
  const container = document.getElementById("chatMessages");
  container.insertAdjacentHTML("beforeend", `
    <div class="chat-bubble-wrap bot" id="${id}">
      <div class="chat-avatar bot-av"><i class="bi bi-robot"></i></div>
      <div class="chat-bubble bot-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
        </div>
      </div>
    </div>`);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function setSendDisabled(disabled) {
  const btn   = document.getElementById("sendBtn");
  const input = document.getElementById("chatInput");
  btn.disabled   = disabled;
  input.disabled = disabled;
}

async function clearChat() {
  await fetch("/api/clear-chat", { method: "POST" });
  const container = document.getElementById("chatMessages");
  container.innerHTML = `
    <div class="chat-welcome">
      <div class="bot-avatar-lg"><i class="bi bi-robot"></i></div>
      <h5>Hello! I'm NutriBot 👋</h5>
      <p>Chat cleared! Ask me anything about nutrition and health.</p>
      <div class="suggestion-grid">
        <button class="suggestion-chip" onclick="sendSuggestion('Create a 7-day Indian vegetarian meal plan for 1800 calories')">🥗 7-Day Meal Plan</button>
        <button class="suggestion-chip" onclick="sendSuggestion('What should I eat for a healthy Indian breakfast?')">🌅 Breakfast Ideas</button>
        <button class="suggestion-chip" onclick="sendSuggestion('Analyze the calories in dal makhani with 2 rotis')">🔥 Calorie Analysis</button>
        <button class="suggestion-chip" onclick="sendSuggestion('Best foods for weight loss in Indian diet')">⚖️ Weight Loss Tips</button>
      </div>
    </div>`;
}

// Auto-resize textarea
function autoResizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

document.addEventListener("DOMContentLoaded", () => {
  const ta = document.getElementById("chatInput");
  if (ta) ta.addEventListener("input", () => autoResizeTextarea(ta));
});

// ── Meal Analyzer ───────────────────────────────────────
async function analyzeMeal() {
  const meal = document.getElementById("mealAnalyzeInput").value.trim();
  if (!meal) { showToast("Please enter a meal to analyze."); return; }

  const result = document.getElementById("mealAnalysisResult");
  result.style.display = "block";
  result.innerHTML = `<div class="d-flex align-items-center gap-2">
    <div class="loading-spinner" style="width:18px;height:18px;border-width:2px;"></div>
    <span>Analyzing…</span></div>`;

  try {
    const res  = await fetch("/api/analyze-meal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meal }),
    });
    const data = await res.json();
    result.innerHTML = markdownToHtml(data.analysis || "Could not analyze this meal.");
  } catch {
    result.innerHTML = "⚠️ Error analyzing meal. Please try again.";
  }
}

// ── Meal Planner ────────────────────────────────────────
async function generateMealPlan() {
  const calories  = parseInt(document.getElementById("planCalories").value, 10);
  const dietType  = document.getElementById("planDietType").value;
  const days      = parseInt(document.getElementById("planDays").value, 10);
  const goalEl    = document.querySelector('input[name="goalRadio"]:checked');
  const goal      = goalEl ? goalEl.value : "maintain";
  const allergies = ["noGluten","noDairy","noNuts","noSoy"]
    .filter(id => document.getElementById(id).checked)
    .map(id => document.getElementById(id).value);

  const btn    = document.getElementById("mealPlanBtn");
  const output = document.getElementById("mealPlanOutput");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating…';
  output.innerHTML = `<div class="empty-state"><div class="loading-spinner"></div><p class="mt-3 text-muted">NutriBot is crafting your personalised meal plan…</p></div>`;

  try {
    const res  = await fetch("/api/meal-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ calories, diet_type: dietType, days, allergies, goal }),
    });
    const data = await res.json();
    output.innerHTML = markdownToHtml(data.plan || "Could not generate a meal plan.");
    document.getElementById("copyMealBtn").style.display = "inline-flex";
  } catch {
    output.innerHTML = "⚠️ Error generating meal plan. Please try again.";
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-magic me-2"></i>Generate AI Meal Plan';
  }
}

function copyMealPlan() {
  const text = document.getElementById("mealPlanOutput").innerText;
  navigator.clipboard.writeText(text).then(() => showToast("Meal plan copied to clipboard!"));
}

// ── BMI Calculator ──────────────────────────────────────
async function calculateBMI() {
  const weight   = parseFloat(document.getElementById("bmiWeight").value);
  const height   = parseFloat(document.getElementById("bmiHeight").value);
  const age      = parseInt(document.getElementById("bmiAge").value, 10);
  const gender   = document.getElementById("bmiGender").value;
  const activity = document.getElementById("bmiActivity").value;

  if (!weight || !height || !age) {
    showToast("Please fill in all fields."); return;
  }

  showLoading("Calculating your BMI and calorie targets…");

  try {
    const res  = await fetch("/api/bmi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ weight, height, age, gender, activity }),
    });
    const d = await res.json();
    hideLoading();

    // Show results
    document.getElementById("bmiResults").style.display = "block";
    document.getElementById("bmiPlaceholder").style.display = "none";

    const bigNum = document.getElementById("bmiBigNum");
    bigNum.textContent = d.bmi;
    bigNum.style.color = d.color;

    const badge = document.getElementById("bmiBadge");
    badge.textContent = d.category;
    badge.style.background = d.color + "22";
    badge.style.color       = d.color;

    document.getElementById("bmiAdvice").textContent = d.advice;
    document.getElementById("resBMR").textContent    = d.bmr;
    document.getElementById("resTDEE").textContent   = d.tdee;
    document.getElementById("resLose").textContent   = d.weight_loss + " kcal";
    document.getElementById("resMaintain").textContent = d.tdee + " kcal";
    document.getElementById("resGain").textContent   = d.weight_gain + " kcal";
    document.getElementById("mtProtein").textContent = d.protein_g + "g";
    document.getElementById("mtCarbs").textContent   = d.carbs_g   + "g";
    document.getElementById("mtFat").textContent     = d.fat_g     + "g";

    // Update dashboard KPIs
    document.getElementById("kpiCalories").querySelector(".kpi-val").textContent = d.tdee;
    document.getElementById("kpiProtein").querySelector(".kpi-val").textContent  = d.protein_g + "g";
    document.getElementById("kpiCarbs").querySelector(".kpi-val").textContent    = d.carbs_g   + "g";
    document.getElementById("kpiFat").querySelector(".kpi-val").textContent      = d.fat_g     + "g";
    updateMacroRing(d.protein_g, d.carbs_g, d.fat_g, d.tdee);

    // Animate BMI number
    animateNumber(bigNum, 0, parseFloat(d.bmi), 1000, 1);
  } catch {
    hideLoading();
    showToast("Error calculating BMI. Please try again.");
  }
}

function animateNumber(el, from, to, duration, decimals) {
  const start = performance.now();
  function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    el.textContent = (from + (to - from) * easeOut(t)).toFixed(decimals);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

function updateMacroRing(prot, carbs, fat, tdee) {
  const total  = prot * 4 + carbs * 4 + fat * 9;
  const circ   = 2 * Math.PI * 40; // r=40
  const protPct  = (prot * 4) / total;
  const carbsPct = (carbs * 4) / total;

  document.querySelector(".ring-protein").setAttribute("stroke-dasharray", `${protPct * circ} ${circ}`);
  document.querySelector(".ring-carbs").setAttribute("stroke-dasharray", `${carbsPct * circ} ${circ}`);
  document.querySelector(".ring-center-label").textContent = tdee;
}

// ── Water Tracker ───────────────────────────────────────
function updateWater(delta) {
  waterGlasses = Math.max(0, Math.min(12, waterGlasses + delta));
  const pct = (waterGlasses / 8) * 100;
  document.getElementById("waterFill").style.height  = Math.min(pct, 100) + "%";
  document.getElementById("waterLabel").textContent  = `${waterGlasses}/8 glasses`;
  document.getElementById("waterCount").textContent  = waterGlasses;
}

// ── Family Profiles ─────────────────────────────────────
function addMemberRow() {
  memberCount++;
  const id  = `member-${memberCount}`;
  const num = memberCount;
  const html = `
    <div class="member-card" id="${id}">
      <button class="member-remove" onclick="removeMember('${id}')" title="Remove">
        <i class="bi bi-x"></i>
      </button>
      <div class="mb-2 fw-600 text-muted" style="font-size:12px;">MEMBER ${num}</div>
      <div class="row g-2">
        <div class="col-12">
          <input type="text" class="form-control form-control-sm" placeholder="Name" data-field="name"/>
        </div>
        <div class="col-6">
          <input type="number" class="form-control form-control-sm" placeholder="Age" min="1" max="100" data-field="age"/>
        </div>
        <div class="col-6">
          <select class="form-select form-select-sm" data-field="gender">
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>
        <div class="col-6">
          <input type="number" class="form-control form-control-sm" placeholder="Weight (kg)" data-field="weight"/>
        </div>
        <div class="col-6">
          <input type="number" class="form-control form-control-sm" placeholder="Height (cm)" data-field="height"/>
        </div>
        <div class="col-12">
          <select class="form-select form-select-sm" data-field="activity">
            <option value="sedentary">Sedentary</option>
            <option value="light">Light Activity</option>
            <option value="moderate" selected>Moderate</option>
            <option value="active">Active</option>
          </select>
        </div>
        <div class="col-6">
          <select class="form-select form-select-sm" data-field="goal">
            <option value="maintain">Maintain</option>
            <option value="lose">Lose Weight</option>
            <option value="gain">Gain Weight</option>
          </select>
        </div>
        <div class="col-6">
          <select class="form-select form-select-sm" data-field="diet">
            <option value="balanced">Balanced</option>
            <option value="vegetarian">Vegetarian</option>
            <option value="vegan">Vegan</option>
            <option value="diabetic">Diabetic</option>
          </select>
        </div>
      </div>
    </div>`;
  document.getElementById("familyMembersForm").insertAdjacentHTML("beforeend", html);
}

function removeMember(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

async function saveFamilyProfiles() {
  const cards = document.querySelectorAll("#familyMembersForm .member-card");
  if (cards.length === 0) { showToast("Please add at least one family member."); return; }

  const members = [];
  cards.forEach(card => {
    const member = {};
    card.querySelectorAll("[data-field]").forEach(el => {
      member[el.dataset.field] = el.value;
    });
    members.push(member);
  });

  const output = document.getElementById("familySummaryOutput");
  output.innerHTML = `<div class="empty-state"><div class="loading-spinner"></div><p class="mt-3 text-muted">Generating family nutrition plan…</p></div>`;
  showLoading("Creating personalised plans for your family…");

  try {
    const res  = await fetch("/api/family-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ members }),
    });
    const data = await res.json();
    hideLoading();
    output.innerHTML = markdownToHtml(data.summary || "Family nutrition summary generated.");
  } catch {
    hideLoading();
    output.innerHTML = "⚠️ Error generating family plan. Please try again.";
  }
}

// ── Loading Overlay ─────────────────────────────────────
function showLoading(text = "Thinking…") {
  document.getElementById("loadingText").textContent = text;
  document.getElementById("loadingOverlay").style.display = "flex";
}
function hideLoading() {
  document.getElementById("loadingOverlay").style.display = "none";
}

// ── Toast ────────────────────────────────────────────────
function showToast(message) {
  document.getElementById("toastBody").textContent = message;
  const toast = new bootstrap.Toast(document.getElementById("appToast"), { delay: 3000 });
  toast.show();
}

// ── Helpers ──────────────────────────────────────────────
function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/\n/g, "<br/>");
}

// ── Init ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Status check
  fetch("/api/status")
    .then(r => r.json())
    .then(d => {
      if (!d.demo_mode) {
        const dot = document.querySelector(".status-dot");
        if (dot) dot.style.background = "#22c55e";
      }
      console.info("NutriBot status:", d);
    })
    .catch(() => {});
});
