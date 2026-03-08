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

function renderSection(title, itemsHtml, emptyText) {
  return `
    <section class="dash-section">
      <div class="dash-section-head">
        <h3>${title}</h3>
      </div>
      ${itemsHtml ? `<div class="dash-grid">${itemsHtml}</div>` : `<div class="dash-empty">${emptyText}</div>`}
    </section>
  `;
}

function renderDashboard(data) {
  const root = $("dashboard-content");
  if (!root) return;

  if (!data) {
    root.innerHTML = "<p>Loading dashboard…</p>";
    return;
  }

  const resumesHtml = (data.my_resumes || []).map((item) => renderResumeCard(item, "resume")).join("");
  const draftsHtml = (data.saved_drafts || []).map((item) => renderResumeCard(item, "draft")).join("");
  const historyHtml = (data.generation_history || []).map((item) => renderHistoryCard(item)).join("");

  root.innerHTML = `
    <section class="dash-section dash-account">
      <h3>Account</h3>
      <p>${data.user.email} ${data.user.is_admin ? "(admin)" : ""}</p>
    </section>
    ${renderSection("My Resumes", resumesHtml, "No resumes yet. Generate your first portfolio to get started.")}
    ${renderSection("Saved Drafts", draftsHtml, "No draft snapshots available yet.")}
    ${renderSection("Generation History", historyHtml, "No generation history yet.")}
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

async function handleDashboardAction(event) {
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
