import { deleteResume, duplicateResume, exportPortfolio, getDashboard, getResume } from "./api.js";
import { navigate } from "./router.js";
import { setState, state, subscribe } from "./state.js";
import { $, contentDispositionFilename, downloadBlob, showBanner, withButtonLoading } from "./utils.js";

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function formatRelative(value) {
  if (!value) return "No activity yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";

  const now = Date.now();
  const diffMs = Math.max(0, now - date.getTime());
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  return formatDate(value);
}

function renderResumeCard(item, sectionType) {
  return `
    <article class="dash-item-card">
      <div class="dash-item-head">
        <h4>${item.title}</h4>
        <span class="dash-badge ${item.status === "published" ? "published" : "draft"}">${item.status || sectionType}</span>
      </div>
      <p class="dash-meta">Updated: ${formatDate(item.updated_at)}</p>
      <div class="dash-actions">
        <button class="btn btn-secondary dash-action" data-action="open" data-id="${item.id}" type="button">Open</button>
        <button class="btn btn-secondary dash-action" data-action="edit" data-id="${item.id}" type="button">Edit</button>
        <button class="btn btn-secondary dash-action" data-action="duplicate" data-id="${item.id}" type="button">Duplicate</button>
        <button class="btn btn-secondary dash-action" data-action="export" data-id="${item.id}" type="button">Export</button>
        <button class="btn btn-danger dash-action" data-action="delete" data-id="${item.id}" type="button">Delete</button>
      </div>
    </article>
  `;
}

function renderHistoryCard(item) {
  return `
    <article class="dash-item-card history">
      <div class="dash-item-head">
        <h4>@${item.username}</h4>
        <span class="dash-badge">Variant ${item.variant_id}</span>
      </div>
      <p class="dash-meta">Template: ${item.template_id || "auto"}</p>
      <p class="dash-meta">Generated: ${formatDate(item.created_at)}</p>
    </article>
  `;
}

function renderCollectionSection({ id, title, subtitle, itemsHtml, emptyTitle, emptyText }) {
  return `
    <section id="${id}" class="dash-section">
      <div class="dash-section-head">
        <h3>${title}</h3>
        ${subtitle ? `<p class="dash-section-subtitle">${subtitle}</p>` : ""}
      </div>
      ${
        itemsHtml
          ? `<div class="dash-grid">${itemsHtml}</div>`
          : `<div class="dash-empty"><strong>${emptyTitle}</strong><span>${emptyText}</span></div>`
      }
    </section>
  `;
}

function renderStatsCards({ resumesCount, draftsCount, exportsCount, lastActivityText }) {
  return `
    <section class="dash-stats-grid" aria-label="Dashboard statistics">
      <article class="dash-stat-card">
        <p class="dash-stat-label">Total Resumes</p>
        <p class="dash-stat-value">${resumesCount}</p>
      </article>
      <article class="dash-stat-card">
        <p class="dash-stat-label">Drafts</p>
        <p class="dash-stat-value">${draftsCount}</p>
      </article>
      <article class="dash-stat-card">
        <p class="dash-stat-label">Exports</p>
        <p class="dash-stat-value">${exportsCount}</p>
      </article>
      <article class="dash-stat-card">
        <p class="dash-stat-label">Last Activity</p>
        <p class="dash-stat-value dash-stat-value-sm">${lastActivityText}</p>
      </article>
    </section>
  `;
}

function renderDashboard(data) {
  const root = $("dashboard-content");
  if (!root) return;

  if (!data) {
    root.innerHTML = '<div class="dash-empty"><strong>Loading dashboard…</strong><span>Please wait while we fetch your latest activity.</span></div>';
    return;
  }

  const resumes = data.my_resumes || [];
  const drafts = data.saved_drafts || [];
  const history = data.generation_history || [];

  const resumesHtml = resumes.map((item) => renderResumeCard(item, "resume")).join("");
  const draftsHtml = drafts.map((item) => renderResumeCard(item, "draft")).join("");
  const historyHtml = history.map((item) => renderHistoryCard(item)).join("");

  const recentTimes = [...resumes, ...drafts, ...history]
    .map((item) => item.updated_at || item.created_at)
    .filter(Boolean)
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
  const lastActivityText = formatRelative(recentTimes[0]);

  const exportCount = resumes.filter((item) => item.status === "published").length;
  const latestResumeId = resumes[0]?.id || drafts[0]?.id || "";

  root.innerHTML = `
    <section class="dash-hero card">
      <div class="dash-hero-copy">
        <p class="dash-eyebrow">Dashboard</p>
        <h3>Welcome back${data.user?.email ? `, ${data.user.email.split("@")[0]}` : ""}.</h3>
        <p>Track your resume pipeline, manage drafts, and continue where you left off.</p>
      </div>
      <div class="dash-hero-actions">
        <button class="btn btn-primary" type="button" data-dash-action="go-generator">Generate Portfolio</button>
        <button class="btn btn-secondary" type="button" data-dash-action="jump-resumes">My Resumes</button>
      </div>
    </section>

    ${renderStatsCards({
      resumesCount: resumes.length,
      draftsCount: drafts.length,
      exportsCount: exportCount,
      lastActivityText,
    })}

    <section class="dash-layout-grid">
      <div class="dash-main-col">
        ${renderCollectionSection({
          id: "dash-resumes",
          title: "Recent Resumes",
          subtitle: "Your latest generated and published portfolios.",
          itemsHtml: resumesHtml,
          emptyTitle: "No resumes yet",
          emptyText: "Generate your first portfolio to start building your resume library.",
        })}
        ${renderCollectionSection({
          id: "dash-drafts",
          title: "Saved Drafts",
          subtitle: "Work-in-progress versions you can refine anytime.",
          itemsHtml: draftsHtml,
          emptyTitle: "No draft snapshots",
          emptyText: "Drafts will appear here after you save or duplicate a resume.",
        })}
        ${renderCollectionSection({
          id: "dash-history",
          title: "Generation History",
          subtitle: "Recent generation activity from your account.",
          itemsHtml: historyHtml,
          emptyTitle: "No generation history",
          emptyText: "Once you generate content, this timeline will show your latest activity.",
        })}
      </div>

      <aside class="dash-side-col">
        <section class="dash-section">
          <div class="dash-section-head">
            <h3>Quick Actions</h3>
          </div>
          <div class="dash-quick-actions">
            <button class="btn btn-primary" type="button" data-dash-action="go-generator">+ New Generation</button>
            <button class="btn btn-secondary" type="button" data-dash-action="jump-drafts">Open Drafts</button>
            <button class="btn btn-secondary" type="button" data-dash-action="jump-history">View History</button>
          </div>
        </section>

        <section class="dash-section dash-account">
          <div class="dash-section-head">
            <h3>Account Summary</h3>
          </div>
          <p class="dash-meta">${data.user.email} ${data.user.is_admin ? "(admin)" : ""}</p>
          <p class="dash-meta">Active resumes: ${resumes.length}</p>
          <p class="dash-meta">Saved drafts: ${drafts.length}</p>
        </section>

        <section class="dash-section">
          <div class="dash-section-head">
            <h3>Export Shortcuts</h3>
          </div>
          <div class="dash-quick-actions">
            <button class="btn btn-secondary" type="button" data-dash-action="export-latest" data-resume-id="${latestResumeId}" ${
              latestResumeId ? "" : "disabled"
            }>Export Latest PDF</button>
            <button class="btn btn-secondary" type="button" data-dash-action="jump-resumes">Go to Resumes</button>
          </div>
        </section>
      </aside>
    </section>
  `;
}

async function loadResumePortfolio(resumeId) {
  const payload = await getResume(resumeId);
  const portfolio = typeof payload.portfolio === "string" ? JSON.parse(payload.portfolio) : payload.portfolio;
  return { ...payload, portfolio };
}

async function exportResume(resumeId) {
  const payload = await loadResumePortfolio(resumeId);
  const response = await exportPortfolio("pdf", {
    portfolio: payload.portfolio,
    filename: `resume-${payload.resume_id}`,
  });
  const fileName = contentDispositionFilename(response.headers.get("content-disposition"), `resume-${payload.resume_id}.pdf`);
  const blob = await response.blob();
  downloadBlob(blob, fileName);
}

async function openResume(resumeId) {
  const payload = await loadResumePortfolio(resumeId);
  const response = await exportPortfolio("html", {
    portfolio: payload.portfolio,
    filename: `resume-${payload.resume_id}`,
  });
  const html = await response.text();
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const blobUrl = URL.createObjectURL(blob);
  window.open(blobUrl, "_blank", "noopener,noreferrer");
  setTimeout(() => URL.revokeObjectURL(blobUrl), 15000);
}

async function editResume(resumeId) {
  const payload = await loadResumePortfolio(resumeId);
  setState({ generatorResult: payload.portfolio });
  navigate("/generator");
  showBanner($("global-banner"), "Loaded resume into generator preview.", "success");
}

function jumpToSection(selector) {
  const node = document.querySelector(selector);
  if (!node) return;
  node.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function handleDashboardAction(event) {
  const quickAction = event.target.closest("[data-dash-action]");
  if (quickAction) {
    const action = quickAction.dataset.dashAction;

    if (action === "go-generator") {
      setState({ generatorResult: null });
      navigate("/generator");
      showBanner($("global-banner"), "Generator ready for a new portfolio.", "info");
      return;
    }

    if (action === "jump-resumes") {
      jumpToSection("#dash-resumes");
      return;
    }

    if (action === "jump-drafts") {
      jumpToSection("#dash-drafts");
      return;
    }

    if (action === "jump-history") {
      jumpToSection("#dash-history");
      return;
    }

    if (action === "export-latest") {
      const resumeId = Number(quickAction.dataset.resumeId);
      if (!resumeId) {
        showBanner($("global-banner"), "No resume available to export yet.", "info");
        return;
      }
      await withButtonLoading(quickAction, "Exporting...", async () => {
        await exportResume(resumeId);
        showBanner($("global-banner"), "Latest resume exported as PDF.", "success");
      }).catch((error) => showBanner($("global-banner"), error.message || "Export failed.", "error"));
      return;
    }
  }

  const button = event.target.closest(".dash-action");
  if (!button) return;
  const action = button.dataset.action;
  const resumeId = Number(button.dataset.id);
  if (!resumeId || !action) return;

  await withButtonLoading(button, "Working...", async () => {
    if (action === "open") {
      await openResume(resumeId);
      return;
    }

    if (action === "edit") {
      await editResume(resumeId);
      return;
    }

    if (action === "duplicate") {
      await duplicateResume(resumeId);
      showBanner($("global-banner"), "Resume duplicated successfully.", "success");
      await loadDashboardData();
      return;
    }

    if (action === "delete") {
      const confirmed = window.confirm("Delete this resume? This action cannot be undone.");
      if (!confirmed) return;
      await deleteResume(resumeId);
      showBanner($("global-banner"), "Resume deleted successfully.", "success");
      await loadDashboardData();
      return;
    }

    if (action === "export") {
      await exportResume(resumeId);
      showBanner($("global-banner"), "Resume exported as PDF.", "success");
    }
  }).catch((error) => showBanner($("global-banner"), error.message || "Action failed.", "error"));
}

export async function loadDashboardData() {
  const data = await getDashboard();
  setState({ dashboardData: data });
  renderDashboard(data);
  return data;
}

export function initDashboard() {
  const root = $("dashboard-content");
  if (root) {
    root.addEventListener("click", (event) => {
      handleDashboardAction(event);
    });
  }

  renderDashboard(state.dashboardData);
  subscribe((nextState) => {
    renderDashboard(nextState.dashboardData);
  });
}
