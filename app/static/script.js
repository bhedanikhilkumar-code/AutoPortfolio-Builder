const form = document.getElementById("builder-form");
const usernameInput = document.getElementById("username");
const themeInput = document.getElementById("theme");
const submitButton = document.getElementById("submit-button");
const statusEl = document.getElementById("status");
const errorBannerEl = document.getElementById("error-banner");
const portfolioEl = document.getElementById("portfolio");
const audioReactiveToggle = document.getElementById("audio-reactive");

const appState = {
  profileData: null,
  generatedPortfolio: null,
  draftPortfolio: null,
  savedPortfolio: null,
  hasUnsavedChanges: false,
  username: "",
  selectedVariantId: 1,
  variants: { 1: null, 2: null, 3: null },
  triesByUsername: {},
};
let parallaxTargets = [];

setupIntroLoader();
const warpController = setupWarpBackground();
setupAudioReactiveToggle();
setupCustomCursor();
setupMouseParallax();
setupRevealAnimations();
setupHeroRotator();
setupMagnetic();

function setupAudioReactiveToggle() {
  if (!audioReactiveToggle || !warpController) return;
  audioReactiveToggle.addEventListener("change", () => {
    warpController.setAudioReactive(Boolean(audioReactiveToggle.checked));
  });
}

themeInput.addEventListener("change", () => {
  if (!appState.draftPortfolio) return;
  updateDraft(() => { appState.draftPortfolio.theme = themeInput.value; });
});

usernameInput.addEventListener("input", () => {
  const incoming = usernameInput.value.trim().toLowerCase();
  if (!incoming || incoming === (appState.username || "").toLowerCase()) return;
  appState.profileData = null;
  appState.variants = { 1: null, 2: null, 3: null };
  resetGenerateButton();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = usernameInput.value.trim();
  const theme = themeInput.value;
  if (!username) return showError("Enter a GitHub username.");

  setLoading(true);
  clearError();

  try {
    const profilePayload = await ensureProfilePayload(username);
    appState.profileData = profilePayload;
    appState.username = username;

    const activeTry = getNextTryIndex(username);
    if (activeTry > 3) {
      setStatus("Try limit reached for this username in this session (3/3).");
      return;
    }

    const variantId = appState.selectedVariantId || 1;
    const variantPortfolio = await generateVariant(profilePayload, theme, variantId, activeTry);

    appState.variants[variantId] = {
      portfolio: deepClone(variantPortfolio),
      tryIndex: activeTry,
      generatedAt: Date.now(),
    };
    appState.triesByUsername[username.toLowerCase()] = activeTry;

    activateVariant(variantId);
    setStatus(`Draft variation ${variantId}/3 generated. Tries used: ${activeTry}/3`);
    setGenerateButtonGenerated();
  } catch (error) {
    portfolioEl.hidden = true;
    portfolioEl.innerHTML = "";
    showError(error.message);
    setGenerateButtonFailed();
  } finally {
    setLoading(false, { preserveLabel: true });
  }
});

async function ensureProfilePayload(username) {
  if (appState.profileData && appState.username.toLowerCase() === username.toLowerCase()) {
    return appState.profileData;
  }
  setStatus("Fetching GitHub profile...");
  const profileResponse = await fetch("/api/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  const profilePayload = await profileResponse.json();
  if (!profileResponse.ok) throw new Error(getErrorMessage(profilePayload, "Failed to fetch profile."));
  return profilePayload;
}

async function generateVariant(profilePayload, theme, variantId, tryIndex) {
  setStatus(`Generating variation ${variantId}/3...`);
  const generateResponse = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...profilePayload, theme, variant_id: variantId, try_index: tryIndex }),
  });
  const portfolioPayload = await generateResponse.json();
  if (!generateResponse.ok) throw new Error(getErrorMessage(portfolioPayload, "Failed to generate portfolio."));
  return portfolioPayload;
}

function getNextTryIndex(username) {
  return (appState.triesByUsername[username.toLowerCase()] || 0) + 1;
}

function activateVariant(variantId) {
  const entry = appState.variants[variantId];
  if (!entry?.portfolio) return;
  appState.selectedVariantId = variantId;
  appState.generatedPortfolio = deepClone(entry.portfolio);
  appState.draftPortfolio = deepClone(entry.portfolio);
  appState.savedPortfolio = deepClone(entry.portfolio);
  appState.hasUnsavedChanges = false;
  renderWorkspace();
}

function setLoading(isLoading, options = {}) {
  const { preserveLabel = false } = options;
  submitButton.disabled = isLoading;
  if (!preserveLabel) {
    submitButton.textContent = isLoading ? "Generating..." : "Generate";
  }
}

function setGenerateButtonGenerated() {
  submitButton.disabled = false;
  submitButton.textContent = "Generated ✅";
}

function setGenerateButtonFailed() {
  submitButton.disabled = false;
  submitButton.textContent = "Failed — Try again";
}

function resetGenerateButton() {
  submitButton.disabled = false;
  submitButton.textContent = "Generate";
}

function setStatus(message) { statusEl.textContent = message; }
function clearError() { errorBannerEl.hidden = true; errorBannerEl.textContent = ""; }
function showError(message) { setStatus("Request failed."); errorBannerEl.hidden = false; errorBannerEl.textContent = message; }

function renderWorkspace() {
  if (!appState.draftPortfolio || !appState.savedPortfolio) {
    portfolioEl.hidden = true;
    portfolioEl.innerHTML = "";
    refreshParallaxTargets();
    return;
  }

  const draft = appState.draftPortfolio;
  const saved = appState.savedPortfolio;
  const profile = getActiveProfile();

  portfolioEl.hidden = false;
  portfolioEl.dataset.theme = saved.theme || themeInput.value;
  portfolioEl.innerHTML = `
    <div class="workspace reveal" data-reveal="up">
      <section class="panel editor glass-card">
        <div>
          <h2>Edit Content</h2>
          <p>Changes apply to the draft immediately. Use Save Edits to update the exportable portfolio state.</p>
          <p class="muted-note"><strong>Draft Variation:</strong> ${appState.selectedVariantId}/3 &nbsp; • &nbsp; Tries used: ${(appState.triesByUsername[(appState.username || "").toLowerCase()] || 0)}/3</p>
        </div>
        <div class="inline-actions" id="variant-tabs">
          <button data-variant-tab="1" class="btn-secondary magnetic" type="button">Variant 1</button>
          <button data-variant-tab="2" class="btn-secondary magnetic" type="button">Variant 2</button>
          <button data-variant-tab="3" class="btn-secondary magnetic" type="button">Variant 3</button>
          <button id="try-another" class="btn-primary magnetic" type="button">Try Another</button>
        </div>
        <div class="inline-actions"><button id="save-edits" class="btn-secondary magnetic" type="button">Save Edits</button><button id="reset-edits" class="btn-danger magnetic" type="button">Reset</button></div>
        <div class="inline-actions"><button id="export-html" class="btn-primary magnetic" type="button">Export HTML</button><button id="export-zip" class="btn-secondary magnetic" type="button">Export ZIP</button><button id="export-pdf" class="btn-secondary magnetic" type="button">Export PDF</button></div>
        <div class="inline-actions"><button id="copy-share-link" class="btn-secondary magnetic" type="button">Copy Resume Link</button></div>
        <p class="muted-note">Share creates a separate resume page and tries to return a short link.</p>
        <div class="editor-section"><h3>${escapeHtml(draft.hero.title)}</h3><label class="field"><span>Headline</span><input id="hero-headline" value="${escapeHtml(draft.hero.content.headline || "")}"></label><label class="field"><span>Subheadline</span><textarea id="hero-subheadline">${escapeHtml(draft.hero.content.subheadline || "")}</textarea></label></div>
        <div class="editor-section"><h3>${escapeHtml(draft.about.title)}</h3><label class="field"><span>Name</span><input id="about-name" value="${escapeHtml(draft.about.content.name || "")}"></label><label class="field"><span>Summary points</span><textarea id="about-summary">${escapeHtml((draft.about.content.summary || []).join("\n"))}</textarea><small>Use one line per summary point.</small></label></div>
        <div class="editor-section"><h3>${escapeHtml(draft.skills.title)}</h3><label class="field"><span>Highlighted skills</span><textarea id="skills-highlighted">${escapeHtml((draft.skills.content.highlighted || []).join(", "))}</textarea><small>Use commas to separate skills.</small></label></div>
        <div class="editor-section"><h3>${escapeHtml(draft.contact.title)}</h3><label class="field"><span>GitHub URL</span><input id="contact-github" value="${escapeHtml(draft.contact.content.github || profile.html_url || "")}"></label><label class="field"><span>Blog</span><input id="contact-blog" value="${escapeHtml(draft.contact.content.blog || "")}"></label><label class="field"><span>Email</span><input id="contact-email" value="${escapeHtml(draft.contact.content.email || "")}"></label><label class="field"><span>Location</span><input id="contact-location" value="${escapeHtml(draft.contact.content.location || "")}"></label></div>
        <div class="editor-section"><h3>${escapeHtml(draft.projects.title)}</h3>${renderProjectEditors(draft.projects.content.items || [])}</div>
      </section>
      <section class="preview-grid">${renderPreview(saved, profile)}</section>
    </div>
  `;

  bindEditorEvents();
  refreshParallaxTargets();
  setupRevealAnimations();
  setupMagnetic();
  setupProjectTilt();
  animateStatCounters();
}

function bindEditorEvents() {
  bindInput("hero-headline", (v) => appState.draftPortfolio.hero.content.headline = v);
  bindInput("hero-subheadline", (v) => appState.draftPortfolio.hero.content.subheadline = v);
  bindInput("about-name", (v) => appState.draftPortfolio.about.content.name = v);
  bindInput("about-summary", (v) => appState.draftPortfolio.about.content.summary = splitLines(v));
  bindInput("skills-highlighted", (v) => appState.draftPortfolio.skills.content.highlighted = splitCsv(v));
  bindInput("contact-github", (v) => appState.draftPortfolio.contact.content.github = v);
  bindInput("contact-blog", (v) => appState.draftPortfolio.contact.content.blog = v);
  bindInput("contact-email", (v) => appState.draftPortfolio.contact.content.email = v);
  bindInput("contact-location", (v) => appState.draftPortfolio.contact.content.location = v);

  document.querySelectorAll("[data-project-index]").forEach((element) => {
    element.addEventListener("input", (event) => {
      const index = Number(event.target.dataset.projectIndex);
      const field = event.target.dataset.projectField;
      updateDraft(() => {
        if (!appState.draftPortfolio.projects.content.items[index]) return;
        appState.draftPortfolio.projects.content.items[index][field] = event.target.value;
      });
    });
  });

  document.querySelectorAll("[data-variant-tab]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const variantId = Number(btn.dataset.variantTab);
      appState.selectedVariantId = variantId;

      if (appState.variants[variantId]?.portfolio) {
        activateVariant(variantId);
        setStatus(`Showing draft variation ${variantId}/3.`);
        return;
      }

      const username = appState.username || usernameInput.value.trim();
      if (!username || !appState.profileData) {
        showError("Generate profile data first.");
        return;
      }

      const activeTry = appState.triesByUsername[username.toLowerCase()] || 0;
      if (activeTry >= 3) {
        setStatus("Try limit reached for this username in this session (3/3).");
        return;
      }

      setLoading(true, { preserveLabel: true });
      try {
        const nextTry = activeTry + 1;
        const generated = await generateVariant(appState.profileData, themeInput.value, variantId, nextTry);
        appState.variants[variantId] = { portfolio: deepClone(generated), tryIndex: nextTry, generatedAt: Date.now() };
        appState.triesByUsername[username.toLowerCase()] = nextTry;
        activateVariant(variantId);
        setGenerateButtonGenerated();
        setStatus(`Draft variation ${variantId}/3 generated. Tries used: ${nextTry}/3`);
      } catch (error) {
        showError(error.message);
      } finally {
        setLoading(false, { preserveLabel: true });
      }
    });
  });

  const tryAnotherBtn = document.getElementById("try-another");
  if (tryAnotherBtn) {
    tryAnotherBtn.addEventListener("click", async () => {
      const username = appState.username || usernameInput.value.trim();
      if (!username || !appState.profileData) {
        showError("Generate profile data first.");
        return;
      }
      const activeTry = appState.triesByUsername[username.toLowerCase()] || 0;
      if (activeTry >= 3) {
        setStatus("Try limit reached for this username in this session (3/3).");
        return;
      }
      setLoading(true, { preserveLabel: true });
      try {
        const nextTry = activeTry + 1;
        const variantId = appState.selectedVariantId || 1;
        const generated = await generateVariant(appState.profileData, themeInput.value, variantId, nextTry);
        appState.variants[variantId] = { portfolio: deepClone(generated), tryIndex: nextTry, generatedAt: Date.now() };
        appState.triesByUsername[username.toLowerCase()] = nextTry;
        activateVariant(variantId);
        setGenerateButtonGenerated();
        setStatus(`Regenerated variation ${variantId}/3. Tries used: ${nextTry}/3`);
      } catch (error) {
        showError(error.message);
      } finally {
        setLoading(false, { preserveLabel: true });
      }
    });
  }

  document.getElementById("save-edits").addEventListener("click", () => {
    appState.savedPortfolio = deepClone(appState.draftPortfolio);
    appState.savedPortfolio.theme = themeInput.value;
    appState.hasUnsavedChanges = false;
    renderWorkspace();
    setStatus("Edits saved. Export uses the current saved version.");
  });

  document.getElementById("reset-edits").addEventListener("click", () => {
    appState.draftPortfolio = deepClone(appState.generatedPortfolio);
    appState.savedPortfolio = deepClone(appState.generatedPortfolio);
    appState.hasUnsavedChanges = false;
    renderWorkspace();
    setStatus("Draft reset to the generated portfolio.");
  });

  document.getElementById("export-html").addEventListener("click", () => exportPortfolio("html"));
  document.getElementById("export-zip").addEventListener("click", () => exportPortfolio("zip"));
  document.getElementById("export-pdf").addEventListener("click", () => exportPortfolio("pdf"));
  document.getElementById("copy-share-link").addEventListener("click", async () => copyShareLink());
}

function bindInput(id, handler) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("input", (event) => updateDraft(() => handler(event.target.value)));
}

function updateDraft(mutate) { mutate(); appState.draftPortfolio.theme = themeInput.value; appState.hasUnsavedChanges = true; setStatus("Draft updated. Save edits to refresh the preview and export state."); }

async function exportPortfolio(format) {
  if (!appState.savedPortfolio) return showError("Generate and save a portfolio before exporting.");
  clearError();
  const endpoint = { html: "/api/export/html", zip: "/api/export/zip", pdf: "/api/export/pdf" }[format] || "/api/export/html";
  setStatus(`Preparing ${format.toUpperCase()} export...`);

  try {
    const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ portfolio: appState.savedPortfolio, filename: buildExportFilename() }) });
    if (!response.ok) throw new Error(getErrorMessage(await parseErrorPayload(response), `Failed to export ${format.toUpperCase()}.`));
    triggerDownload(await response.blob(), readDownloadName(response.headers.get("Content-Disposition"), format));
    setStatus(`${format.toUpperCase()} export downloaded.`);
  } catch (error) { showError(error.message); }
}

function triggerDownload(blob, fileName) { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = fileName; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url); }
async function copyShareLink() { if (!appState.savedPortfolio) return showError("Generate and save a portfolio before creating a share link."); clearError(); try { const shareUrl = await buildShareUrl(); await writeToClipboard(shareUrl); setStatus("Share link copied to clipboard."); } catch (error) { showError(error.message); } }

function renderPreview(portfolioData, profile) {
  const timeline = ["Freelance / Open Source Contributions", "Built automation tools for portfolio workflows", "Shipping UI and full-stack product iterations"];
  const testimonials = ["Fast execution and clean UI taste.", "Great at turning ideas into working products."];

  const sectionMap = {
    hero: `<section class="panel preview-panel wide glass-card reveal" data-reveal="up"><p>${escapeHtml(portfolioData.hero.title)}</p><h2>${escapeHtml(portfolioData.hero.content.headline || "")}</h2><p>${escapeHtml(portfolioData.hero.content.subheadline || "")}</p><div class="stats">${renderStat("Repos", portfolioData.hero.content.stats.public_repos)}${renderStat("Followers", portfolioData.hero.content.stats.followers)}${renderStat("Following", portfolioData.hero.content.stats.following)}</div></section>`,
    about: `<section class="panel preview-panel glass-card reveal" data-reveal="up"><p>${escapeHtml(portfolioData.about.title)}</p><h2>${escapeHtml(portfolioData.about.content.name || "")}</h2><ul>${(portfolioData.about.content.summary || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>Details coming soon.</li>"}</ul></section>`,
    skills: `<section class="panel preview-panel glass-card reveal" data-reveal="up"><p>${escapeHtml(portfolioData.skills.title)}</p><h2>Highlighted Skills</h2><div class="tags">${(portfolioData.skills.content.highlighted || []).map(renderTag).join("") || "<span class='tag'>No detected skills yet</span>"}</div></section>`,
    projects: `<section class="panel preview-panel wide glass-card reveal" data-reveal="up"><p>${escapeHtml(portfolioData.projects.title)}</p><h2>Featured Work</h2><div class="project-list">${(portfolioData.projects.content.items || []).map((project) => `<article class="project glass-card tilt-card"><div class="project-header"><strong>${escapeHtml(project.name || "Untitled project")}</strong>${safeInlineLink(project.url, "Repository")}</div><p>${escapeHtml(project.description || "Project details coming soon.")}</p><div class="tags">${project.language ? renderTag(project.language) : ""}${(project.topics || []).map(renderTag).join("")}</div></article>`).join("") || "<p>No repositories available.</p>"}</div></section>`,
    contact: `<section class="panel preview-panel wide glass-card reveal" data-reveal="up"><p>${escapeHtml(portfolioData.contact.title)}</p><h2>Contact</h2>${safeLinkLine(portfolioData.contact.content.github || profile.html_url, portfolioData.contact.content.github || profile.html_url)}${safeLinkLine(portfolioData.contact.content.blog, portfolioData.contact.content.blog)}${portfolioData.contact.content.email ? `<p>${escapeHtml(portfolioData.contact.content.email)}</p>` : ""}${portfolioData.contact.content.location ? `<p>${escapeHtml(portfolioData.contact.content.location)}</p>` : ""}</section>`,
  };

  const ordered = portfolioData.hero.content.section_order || ["hero", "about", "skills", "projects", "contact"];
  const dynamicSections = ordered.map((key) => sectionMap[key] || "").join("");

  return `${dynamicSections}
    <section class="panel preview-panel glass-card reveal" data-reveal="up"><p>Experience Timeline</p><h2>Journey</h2>${timeline.map((x) => `<div class='timeline-item'>${escapeHtml(x)}</div>`).join("")}</section>
    <section class="panel preview-panel glass-card reveal" data-reveal="up"><p>Testimonials</p><h2>Feedback</h2>${testimonials.map((x) => `<div class='testimonial-item'>“${escapeHtml(x)}”</div>`).join("")}</section>
    <section class="panel preview-panel wide glass-card reveal" data-reveal="up"><p>Now Building</p><h2>Current Focus</h2><div class="now-item">⚙️ Improving developer portfolio generation quality, speed, and export flexibility.</div></section>`;
}

function renderProjectEditors(projects) { if (!projects.length) return "<p>No repositories available to edit.</p>"; return projects.map((project, index) => `<div class="project-editor"><label class="field"><span>Project ${index + 1} name</span><input data-project-index="${index}" data-project-field="name" value="${escapeHtml(project.name || "")}"></label><label class="field"><span>Description</span><textarea data-project-index="${index}" data-project-field="description">${escapeHtml(project.description || "")}</textarea></label></div>`).join(""); }
function renderStat(label, value) { return `<div class="stat"><strong data-count='${escapeHtml(String(value ?? 0))}'>0</strong><span>${escapeHtml(label)}</span></div>`; }
function renderTag(value) { return `<span class="tag">${escapeHtml(value)}</span>`; }
function safeInlineLink(href, label) { if (!href || !/^https?:\/\//.test(href)) return ""; return `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`; }
function safeLinkLine(href, label) { const link = safeInlineLink(href, label); return link ? `<p>${link}</p>` : ""; }
function splitLines(value) { return value.split("\n").map((item) => item.trim()).filter(Boolean); }
function splitCsv(value) { return value.split(",").map((item) => item.trim()).filter(Boolean); }
function buildExportFilename() { const source = appState.savedPortfolio?.about?.content?.name || appState.profileData?.profile?.username || "portfolio"; return source.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64) || "portfolio"; }
function readDownloadName(contentDisposition, format) { const match = contentDisposition && contentDisposition.match(/filename="([^"]+)"/); return (match && match[1]) ? match[1] : `${buildExportFilename()}.${format}`; }
async function buildShareUrl() { const response = await fetch("/api/share", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ portfolio: appState.savedPortfolio, filename: buildExportFilename(), use_short_link: true }) }); if (!response.ok) throw new Error(getErrorMessage(await parseErrorPayload(response), "Failed to create share link.")); const payload = await response.json(); return payload.share_url || payload.resume_url; }
function getActiveProfile() { return appState.profileData?.profile || { html_url: "" }; }
async function writeToClipboard(value) { if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(value); const input = document.createElement("input"); input.value = value; document.body.appendChild(input); input.select(); if (!document.execCommand("copy")) { input.remove(); throw new Error("Clipboard access is unavailable in this browser."); } input.remove(); }
async function parseErrorPayload(response) { const contentType = response.headers.get("Content-Type") || ""; return contentType.includes("application/json") ? response.json() : { detail: await response.text() }; }
function getErrorMessage(payload, fallbackMessage) { return payload?.error?.message || payload?.detail || fallbackMessage; }
function deepClone(value) { return JSON.parse(JSON.stringify(value)); }
function escapeHtml(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;"); }

function setupIntroLoader() {
  const loader = document.getElementById("intro-loader");
  const bar = document.getElementById("intro-loader-bar");
  if (!loader || !bar) return;

  let progress = 0;
  const timer = setInterval(() => {
    progress = Math.min(92, progress + Math.random() * 18);
    bar.style.width = `${progress}%`;
  }, 110);

  window.addEventListener("load", () => {
    clearInterval(timer);
    bar.style.width = "100%";
    setTimeout(() => loader.classList.add("hidden"), 250);
  }, { once: true });
}

function setupCustomCursor() {
  if (window.matchMedia("(hover: none), (pointer: coarse)").matches) return;
  const dot = document.getElementById("cursor-dot");
  const ring = document.getElementById("cursor-ring");
  if (!dot || !ring) return;

  let x = window.innerWidth / 2;
  let y = window.innerHeight / 2;
  let rx = x;
  let ry = y;

  document.addEventListener("mousemove", (e) => {
    x = e.clientX;
    y = e.clientY;
    dot.style.transform = `translate(${x}px, ${y}px)`;
  });

  const animate = () => {
    rx += (x - rx) * 0.16;
    ry += (y - ry) * 0.16;
    ring.style.transform = `translate(${rx}px, ${ry}px)`;
    requestAnimationFrame(animate);
  };
  animate();
}

function setupWarpBackground() {
  const canvas = document.getElementById("bg-animation");
  if (!canvas) return null;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return null;

  let width = 0;
  let height = 0;
  let rafId = null;
  let audioReactive = false;
  const DPR = Math.min(window.devicePixelRatio || 1, 1.75);
  let particles = [];

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * DPR);
    canvas.height = Math.floor(height * DPR);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

    particles = Array.from({ length: 200 }, () => createParticle());
  }

  function createParticle() {
    const angle = Math.random() * Math.PI * 2;
    const speed = (Math.random() * 6) - 3;
    const speed2 = (Math.random() * 6) - 3;
    return {
      x: width / 2,
      y: height / 2,
      vx: speed,
      vy: speed2,
      size: Math.random() * 2 + 1,
      angle,
    };
  }

  function resetParticle(p) {
    p.x = width / 2;
    p.y = height / 2;
    p.vx = (Math.random() - 0.5) * 6;
    p.vy = (Math.random() - 0.5) * 6;
    p.size = Math.random() * 2 + 1;
  }

  function frame(now = 0) {
    const pulse = audioReactive ? (0.8 + Math.abs(Math.sin(now * 0.0045)) * 0.8) : 1;

    ctx.fillStyle = "rgba(2,6,23,0.25)";
    ctx.fillRect(0, 0, width, height);

    particles.forEach((p) => {
      p.x += p.vx * pulse;
      p.y += p.vy * pulse;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * (audioReactive ? 1.2 : 1), 0, Math.PI * 2);
      ctx.fillStyle = audioReactive ? "rgba(56, 189, 248, 0.95)" : "#00eaff";
      ctx.shadowColor = audioReactive ? "rgba(56, 189, 248, 0.95)" : "rgba(0, 234, 255, 0.85)";
      ctx.shadowBlur = audioReactive ? 18 : 10;
      ctx.fill();

      if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) {
        resetParticle(p);
      }
    });

    rafId = requestAnimationFrame(frame);
  }

  const stop = () => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
  };

  const start = () => {
    if (!rafId && !reduced) rafId = requestAnimationFrame(frame);
  };

  resize();
  start();

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      stop();
      resize();
      start();
    }, 120);
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });

  return {
    setAudioReactive(value) {
      audioReactive = value;
    },
  };
}

function setupMouseParallax() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  refreshParallaxTargets();
  document.addEventListener("mousemove", (event) => {
    if (!parallaxTargets.length) return;
    const x = (event.clientX / window.innerWidth - 0.5) * 2;
    const y = (event.clientY / window.innerHeight - 0.5) * 2;
    parallaxTargets.forEach((el) => {
      const depth = Number(el.dataset.depth || 1);
      el.style.transform = `translate3d(${-x * 7 * depth}px, ${-y * 6 * depth}px, 0)`;
    });
  });
  document.addEventListener("mouseleave", () => parallaxTargets.forEach((el) => { el.style.transform = "translate3d(0,0,0)"; }));
}

function refreshParallaxTargets() { parallaxTargets = Array.from(document.querySelectorAll(".panel, .editor-section, .project")); parallaxTargets.forEach((el, index) => { if (!el.dataset.depth) el.dataset.depth = String(0.75 + (index % 3) * 0.15); }); }
function setupRevealAnimations() { const items = document.querySelectorAll(".reveal"); if (!items.length) return; const io = new IntersectionObserver((entries) => { entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("reveal-in"); io.unobserve(entry.target); } }); }, { threshold: 0.14 }); items.forEach((el) => io.observe(el)); }
function setupHeroRotator() { const el = document.getElementById("hero-rotator"); if (!el) return; const lines = ["AI Portfolio. Auto-built. Always fresh.", "From GitHub profile to premium personal brand.", "Dark, modern, and ready to impress recruiters."]; let i = 0; setInterval(() => { i = (i + 1) % lines.length; el.style.opacity = "0"; setTimeout(() => { el.textContent = lines[i]; el.style.opacity = "1"; }, 180); }, 3000); }
function setupMagnetic() { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return; document.querySelectorAll(".magnetic").forEach((btn) => { btn.onmousemove = (e) => { const r = btn.getBoundingClientRect(); const x = e.clientX - (r.left + r.width / 2); const y = e.clientY - (r.top + r.height / 2); btn.style.transform = `translate(${x * 0.14}px, ${y * 0.16}px)`; }; btn.onmouseleave = () => { btn.style.transform = "translate(0,0)"; }; }); }
function setupProjectTilt() { if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return; document.querySelectorAll(".tilt-card").forEach((card) => { card.addEventListener("mousemove", (e) => { const r = card.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - 0.5; const y = (e.clientY - r.top) / r.height - 0.5; card.style.transform = `rotateX(${(-y * 8).toFixed(2)}deg) rotateY(${(x * 10).toFixed(2)}deg)`; }); card.addEventListener("mouseleave", () => { card.style.transform = "rotateX(0deg) rotateY(0deg)"; }); }); }
function animateStatCounters() { const items = document.querySelectorAll("[data-count]"); items.forEach((el) => { const target = Number(el.dataset.count || 0); if (!Number.isFinite(target)) return; const start = performance.now(); const dur = 900; const step = (now) => { const t = Math.min(1, (now - start) / dur); const eased = 1 - Math.pow(1 - t, 3); el.textContent = Math.round(target * eased).toString(); if (t < 1) requestAnimationFrame(step); }; requestAnimationFrame(step); }); }
