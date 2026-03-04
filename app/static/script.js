const form = document.getElementById("builder-form");
const usernameInput = document.getElementById("username");
const themeInput = document.getElementById("theme");
const submitButton = document.getElementById("submit-button");
const statusEl = document.getElementById("status");
const errorBannerEl = document.getElementById("error-banner");
const portfolioEl = document.getElementById("portfolio");

const appState = {
  profileData: null,
  generatedPortfolio: null,
  draftPortfolio: null,
  savedPortfolio: null,
  hasUnsavedChanges: false,
};

let parallaxTargets = [];

setupWarpBackground();
setupMouseParallax();

themeInput.addEventListener("change", () => {
  if (!appState.draftPortfolio) {
    return;
  }
  updateDraft(() => {
    appState.draftPortfolio.theme = themeInput.value;
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = usernameInput.value.trim();
  const theme = themeInput.value;
  if (!username) {
    showError("Enter a GitHub username.");
    return;
  }

  setLoading(true);
  clearError();
  setStatus("Fetching GitHub profile...");

  try {
    const profileResponse = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });

    const profilePayload = await profileResponse.json();
    if (!profileResponse.ok) {
      throw new Error(getErrorMessage(profilePayload, "Failed to fetch profile."));
    }

    setStatus("Generating portfolio...");

    const generateResponse = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...profilePayload, theme }),
    });

    const portfolioPayload = await generateResponse.json();
    if (!generateResponse.ok) {
      throw new Error(getErrorMessage(portfolioPayload, "Failed to generate portfolio."));
    }

    appState.profileData = profilePayload;
    appState.generatedPortfolio = deepClone(portfolioPayload);
    appState.draftPortfolio = deepClone(portfolioPayload);
    appState.savedPortfolio = deepClone(portfolioPayload);
    appState.hasUnsavedChanges = false;

    renderWorkspace();
    setStatus("Portfolio generated. Edit the fields, then save before exporting.");
  } catch (error) {
    portfolioEl.hidden = true;
    portfolioEl.innerHTML = "";
    showError(error.message);
  } finally {
    setLoading(false);
  }
});

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Working..." : "Generate";
}

function setStatus(message) {
  statusEl.textContent = message;
}

function clearError() {
  errorBannerEl.hidden = true;
  errorBannerEl.textContent = "";
}

function showError(message) {
  setStatus("Request failed.");
  errorBannerEl.hidden = false;
  errorBannerEl.textContent = message;
}

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
    <div class="workspace">
      <section class="panel editor glass-card">
        <div>
          <h2>Edit Content</h2>
          <p>Changes apply to the draft immediately. Use Save Edits to update the exportable portfolio state.</p>
        </div>
        <div class="inline-actions">
          <button id="save-edits" class="btn-secondary" type="button">Save Edits</button>
          <button id="reset-edits" class="btn-danger" type="button">Reset</button>
        </div>
        <div class="inline-actions">
          <button id="export-html" class="btn-primary" type="button">Export HTML</button>
          <button id="export-zip" class="btn-secondary" type="button">Export ZIP</button>
          <button id="export-pdf" class="btn-secondary" type="button">Export PDF</button>
        </div>
        <div class="inline-actions">
          <button id="copy-share-link" class="btn-secondary" type="button">Copy Resume Link</button>
        </div>
        <p class="muted-note">Share creates a separate resume page and tries to return a short link.</p>
        <div class="editor-section">
          <h3>${escapeHtml(draft.hero.title)}</h3>
          <label class="field">
            <span>Headline</span>
            <input id="hero-headline" value="${escapeHtml(draft.hero.content.headline || "")}">
          </label>
          <label class="field">
            <span>Subheadline</span>
            <textarea id="hero-subheadline">${escapeHtml(draft.hero.content.subheadline || "")}</textarea>
          </label>
        </div>
        <div class="editor-section">
          <h3>${escapeHtml(draft.about.title)}</h3>
          <label class="field">
            <span>Name</span>
            <input id="about-name" value="${escapeHtml(draft.about.content.name || "")}">
          </label>
          <label class="field">
            <span>Summary points</span>
            <textarea id="about-summary">${escapeHtml((draft.about.content.summary || []).join("\n"))}</textarea>
            <small>Use one line per summary point.</small>
          </label>
        </div>
        <div class="editor-section">
          <h3>${escapeHtml(draft.skills.title)}</h3>
          <label class="field">
            <span>Highlighted skills</span>
            <textarea id="skills-highlighted">${escapeHtml((draft.skills.content.highlighted || []).join(", "))}</textarea>
            <small>Use commas to separate skills.</small>
          </label>
        </div>
        <div class="editor-section">
          <h3>${escapeHtml(draft.contact.title)}</h3>
          <label class="field">
            <span>GitHub URL</span>
            <input id="contact-github" value="${escapeHtml(draft.contact.content.github || profile.html_url || "")}">
          </label>
          <label class="field">
            <span>Blog</span>
            <input id="contact-blog" value="${escapeHtml(draft.contact.content.blog || "")}">
          </label>
          <label class="field">
            <span>Email</span>
            <input id="contact-email" value="${escapeHtml(draft.contact.content.email || "")}">
          </label>
          <label class="field">
            <span>Location</span>
            <input id="contact-location" value="${escapeHtml(draft.contact.content.location || "")}">
          </label>
        </div>
        <div class="editor-section">
          <h3>${escapeHtml(draft.projects.title)}</h3>
          ${renderProjectEditors(draft.projects.content.items || [])}
        </div>
      </section>

      <section class="preview-grid">
        ${renderPreview(saved, profile)}
      </section>
    </div>
  `;

  bindEditorEvents();
  refreshParallaxTargets();
}

function bindEditorEvents() {
  document.getElementById("hero-headline").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.hero.content.headline = event.target.value;
    });
  });

  document.getElementById("hero-subheadline").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.hero.content.subheadline = event.target.value;
    });
  });

  document.getElementById("about-name").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.about.content.name = event.target.value;
    });
  });

  document.getElementById("about-summary").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.about.content.summary = splitLines(event.target.value);
    });
  });

  document.getElementById("skills-highlighted").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.skills.content.highlighted = splitCsv(event.target.value);
    });
  });

  document.getElementById("contact-github").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.contact.content.github = event.target.value;
    });
  });

  document.getElementById("contact-blog").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.contact.content.blog = event.target.value;
    });
  });

  document.getElementById("contact-email").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.contact.content.email = event.target.value;
    });
  });

  document.getElementById("contact-location").addEventListener("input", (event) => {
    updateDraft(() => {
      appState.draftPortfolio.contact.content.location = event.target.value;
    });
  });

  document.querySelectorAll("[data-project-index]").forEach((element) => {
    element.addEventListener("input", (event) => {
      const index = Number(event.target.dataset.projectIndex);
      const field = event.target.dataset.projectField;
      updateDraft(() => {
        if (!appState.draftPortfolio.projects.content.items[index]) {
          return;
        }
        appState.draftPortfolio.projects.content.items[index][field] = event.target.value;
      });
    });
  });

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

  document.getElementById("export-html").addEventListener("click", () => {
    exportPortfolio("html");
  });

  document.getElementById("export-zip").addEventListener("click", () => {
    exportPortfolio("zip");
  });

  document.getElementById("export-pdf").addEventListener("click", () => {
    exportPortfolio("pdf");
  });

  document.getElementById("copy-share-link").addEventListener("click", async () => {
    await copyShareLink();
  });
}

function updateDraft(mutate) {
  mutate();
  appState.draftPortfolio.theme = themeInput.value;
  appState.hasUnsavedChanges = true;
  setStatus("Draft updated. Save edits to refresh the preview and export state.");
}

async function exportPortfolio(format) {
  if (!appState.savedPortfolio) {
    showError("Generate and save a portfolio before exporting.");
    return;
  }

  clearError();
  const endpoint = {
    html: "/api/export/html",
    zip: "/api/export/zip",
    pdf: "/api/export/pdf",
  }[format] || "/api/export/html";
  setStatus(`Preparing ${format.toUpperCase()} export...`);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio: appState.savedPortfolio,
        filename: buildExportFilename(),
      }),
    });

    if (!response.ok) {
      const payload = await parseErrorPayload(response);
      throw new Error(getErrorMessage(payload, `Failed to export ${format.toUpperCase()}.`));
    }

    const blob = await response.blob();
    triggerDownload(blob, readDownloadName(response.headers.get("Content-Disposition"), format));
    setStatus(`${format.toUpperCase()} export downloaded.`);
  } catch (error) {
    showError(error.message);
  }
}

function triggerDownload(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function copyShareLink() {
  if (!appState.savedPortfolio) {
    showError("Generate and save a portfolio before creating a share link.");
    return;
  }

  clearError();

  try {
    const shareUrl = await buildShareUrl();
    await writeToClipboard(shareUrl);
    setStatus("Share link copied to clipboard.");
  } catch (error) {
    showError(error.message);
  }
}

function renderPreview(portfolioData, profile) {
  return `
    <section class="panel preview-panel wide glass-card">
      <p>${escapeHtml(portfolioData.hero.title)}</p>
      <h2>${escapeHtml(portfolioData.hero.content.headline || "")}</h2>
      <p>${escapeHtml(portfolioData.hero.content.subheadline || "")}</p>
      <div class="stats">
        ${renderStat("Repos", portfolioData.hero.content.stats.public_repos)}
        ${renderStat("Followers", portfolioData.hero.content.stats.followers)}
        ${renderStat("Following", portfolioData.hero.content.stats.following)}
      </div>
    </section>
    <section class="panel preview-panel glass-card">
      <p>${escapeHtml(portfolioData.about.title)}</p>
      <h2>${escapeHtml(portfolioData.about.content.name || "")}</h2>
      <ul>${(portfolioData.about.content.summary || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>Details coming soon.</li>"}</ul>
    </section>
    <section class="panel preview-panel glass-card">
      <p>${escapeHtml(portfolioData.skills.title)}</p>
      <h2>Highlighted Skills</h2>
      <div class="tags">${(portfolioData.skills.content.highlighted || []).map(renderTag).join("") || "<span class='tag'>No detected skills yet</span>"}</div>
    </section>
    <section class="panel preview-panel wide glass-card">
      <p>${escapeHtml(portfolioData.projects.title)}</p>
      <h2>Featured Work</h2>
      <div class="project-list">
        ${(portfolioData.projects.content.items || []).map((project) => `
          <article class="project glass-card">
            <div class="project-header">
              <strong>${escapeHtml(project.name || "Untitled project")}</strong>
              ${safeInlineLink(project.url, "Repository")}
            </div>
            <p>${escapeHtml(project.description || "Project details coming soon.")}</p>
            <div class="tags">
              ${project.language ? renderTag(project.language) : ""}
              ${(project.topics || []).map(renderTag).join("")}
            </div>
          </article>
        `).join("") || "<p>No repositories available.</p>"}
      </div>
    </section>
    <section class="panel preview-panel wide glass-card">
      <p>${escapeHtml(portfolioData.contact.title)}</p>
      <h2>Contact</h2>
      ${safeLinkLine(portfolioData.contact.content.github || profile.html_url, portfolioData.contact.content.github || profile.html_url)}
      ${safeLinkLine(portfolioData.contact.content.blog, portfolioData.contact.content.blog)}
      ${portfolioData.contact.content.email ? `<p>${escapeHtml(portfolioData.contact.content.email)}</p>` : ""}
      ${portfolioData.contact.content.location ? `<p>${escapeHtml(portfolioData.contact.content.location)}</p>` : ""}
    </section>
  `;
}

function renderProjectEditors(projects) {
  if (!projects.length) {
    return "<p>No repositories available to edit.</p>";
  }

  return projects.map((project, index) => `
    <div class="project-editor">
      <label class="field">
        <span>Project ${index + 1} name</span>
        <input data-project-index="${index}" data-project-field="name" value="${escapeHtml(project.name || "")}">
      </label>
      <label class="field">
        <span>Description</span>
        <textarea data-project-index="${index}" data-project-field="description">${escapeHtml(project.description || "")}</textarea>
      </label>
    </div>
  `).join("");
}

function renderStat(label, value) {
  return `<div class="stat"><strong>${escapeHtml(String(value ?? 0))}</strong><span>${escapeHtml(label)}</span></div>`;
}

function renderTag(value) {
  return `<span class="tag">${escapeHtml(value)}</span>`;
}

function safeInlineLink(href, label) {
  if (!href || !/^https?:\/\//.test(href)) {
    return "";
  }
  return `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
}

function safeLinkLine(href, label) {
  const link = safeInlineLink(href, label);
  return link ? `<p>${link}</p>` : "";
}

function splitLines(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitCsv(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildExportFilename() {
  const source = appState.savedPortfolio?.about?.content?.name
    || appState.profileData?.profile?.username
    || "portfolio";

  return source
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64) || "portfolio";
}

function readDownloadName(contentDisposition, format) {
  const match = contentDisposition && contentDisposition.match(/filename="([^"]+)"/);
  if (match && match[1]) {
    return match[1];
  }
  return `${buildExportFilename()}.${format}`;
}

async function buildShareUrl() {
  const response = await fetch("/api/share", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      portfolio: appState.savedPortfolio,
      filename: buildExportFilename(),
      use_short_link: true,
    }),
  });

  if (!response.ok) {
    const payload = await parseErrorPayload(response);
    throw new Error(getErrorMessage(payload, "Failed to create share link."));
  }

  const payload = await response.json();
  return payload.share_url || payload.resume_url;
}

function getActiveProfile() {
  return appState.profileData?.profile || {
    html_url: "",
  };
}

async function writeToClipboard(value) {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    await navigator.clipboard.writeText(value);
    return;
  }

  const input = document.createElement("input");
  input.value = value;
  document.body.appendChild(input);
  input.select();

  if (!document.execCommand("copy")) {
    input.remove();
    throw new Error("Clipboard access is unavailable in this browser.");
  }

  input.remove();
}

async function parseErrorPayload(response) {
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return { detail: await response.text() };
}

function getErrorMessage(payload, fallbackMessage) {
  if (payload && payload.error && payload.error.message) {
    return payload.error.message;
  }
  if (payload && payload.detail) {
    return payload.detail;
  }
  return fallbackMessage;
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setupWarpBackground() {
  const canvas = document.getElementById("warp-canvas");
  if (!canvas) return;

  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return;

  let width = 0;
  let height = 0;
  let centerX = 0;
  let centerY = 0;
  let maxRadius = 0;
  let particleCount = 0;
  let particles = [];
  let rafId = null;

  const DPR = Math.min(window.devicePixelRatio || 1, 1.8);

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    centerX = width * 0.5;
    centerY = height * 0.5;
    maxRadius = Math.hypot(centerX, centerY) + 120;

    canvas.width = Math.floor(width * DPR);
    canvas.height = Math.floor(height * DPR);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

    particleCount = Math.max(70, Math.min(180, Math.floor((width * height) / 12000)));
    particles = Array.from({ length: particleCount }, () => createParticle(true));
  }

  function createParticle(randomDepth = false) {
    const angle = Math.random() * Math.PI * 2;
    const radius = randomDepth ? Math.random() * maxRadius : maxRadius;
    const speed = 0.9 + Math.random() * 2.1;
    const glow = 0.3 + Math.random() * 0.7;

    return {
      angle,
      radius,
      speed,
      glow,
      lastX: centerX + Math.cos(angle) * radius,
      lastY: centerY + Math.sin(angle) * radius,
    };
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < particles.length; i += 1) {
      const p = particles[i];
      p.radius -= p.speed;

      if (p.radius < 2) {
        particles[i] = createParticle(false);
        continue;
      }

      const x = centerX + Math.cos(p.angle) * p.radius;
      const y = centerY + Math.sin(p.angle) * p.radius;

      const streakLength = (1 - p.radius / maxRadius) * 34 + 4;
      const dx = x - centerX;
      const dy = y - centerY;
      const mag = Math.hypot(dx, dy) || 1;
      const tailX = x + (dx / mag) * streakLength;
      const tailY = y + (dy / mag) * streakLength;

      const alpha = Math.max(0.12, 1 - p.radius / maxRadius) * p.glow;
      ctx.strokeStyle = `rgba(56, 189, 248, ${alpha})`;
      ctx.lineWidth = 1.2 + alpha * 1.8;
      ctx.shadowColor = "rgba(34, 211, 238, 0.8)";
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.moveTo(tailX, tailY);
      ctx.lineTo(x, y);
      ctx.stroke();

      p.lastX = x;
      p.lastY = y;
    }

    rafId = window.requestAnimationFrame(draw);
  }

  resize();

  if (!prefersReduced) {
    draw();
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
      resize();
      if (!prefersReduced) {
        draw();
      }
    }, 120);
  });
}

function setupMouseParallax() {
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) return;

  refreshParallaxTargets();

  document.addEventListener("mousemove", (event) => {
    if (!parallaxTargets.length) return;

    const x = (event.clientX / window.innerWidth - 0.5) * 2;
    const y = (event.clientY / window.innerHeight - 0.5) * 2;

    parallaxTargets.forEach((el) => {
      const depth = Number(el.dataset.depth || 1);
      const tx = -x * 7 * depth;
      const ty = -y * 6 * depth;
      el.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
    });
  });

  document.addEventListener("mouseleave", () => {
    parallaxTargets.forEach((el) => {
      el.style.transform = "translate3d(0, 0, 0)";
    });
  });
}

function refreshParallaxTargets() {
  parallaxTargets = Array.from(document.querySelectorAll(".panel, .editor-section, .project"));
  parallaxTargets.forEach((el, index) => {
    if (!el.dataset.depth) {
      el.dataset.depth = String(0.8 + (index % 3) * 0.15);
    }
  });
}
