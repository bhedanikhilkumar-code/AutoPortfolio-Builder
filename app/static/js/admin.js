import { exportAdminCsv, getAdminActivity, getAdminResumes, getAdminStats, getAdminUsers } from "./api.js";
import { isAdmin } from "./state.js";
import { $, contentDispositionFilename, downloadBlob, showBanner, withButtonLoading } from "./utils.js";

function ensureAdminUiState() {
  if (!isAdmin()) {
    throw new Error("Admin privileges required.");
  }
}

function renderAdminData(stats, users, resumes, activity) {
  const root = $("admin-content");
  if (!root) return;

  const userItems = (users.users || []).map((item) => `<li>${item.email} ${item.is_admin ? "(admin)" : ""}</li>`).join("") || "<li>No users.</li>";
  const resumeItems = (resumes.resumes || []).map((item) => `<li>#${item.id} ${item.title} · ${item.owner_email}</li>`).join("") || "<li>No resumes.</li>";
  const activityItems = (activity.logs || []).map((item) => `<li>${item.action} ${item.target_type}#${item.target_id}</li>`).join("") || "<li>No activity.</li>";

  root.innerHTML = `
    <section>
      <h3>Stats</h3>
      <p>Users: ${stats.total_users} | Admins: ${stats.total_admins} | Resumes: ${stats.total_resumes} | Generations: ${stats.total_generations}</p>
    </section>
    <section>
      <h3>Users</h3>
      <ul>${userItems}</ul>
    </section>
    <section>
      <h3>Resumes</h3>
      <ul>${resumeItems}</ul>
    </section>
    <section>
      <h3>Activity</h3>
      <ul>${activityItems}</ul>
    </section>
  `;
}

export async function refreshAdminData() {
  ensureAdminUiState();
  const [stats, users, resumes, activity] = await Promise.all([
    getAdminStats(),
    getAdminUsers(),
    getAdminResumes(),
    getAdminActivity(),
  ]);
  renderAdminData(stats, users, resumes, activity);
}

async function exportCsv(path, fallbackName) {
  ensureAdminUiState();
  const response = await exportAdminCsv(path);
  const fileName = contentDispositionFilename(response.headers.get("content-disposition"), fallbackName);
  const blob = await response.blob();
  downloadBlob(blob, fileName);
}

export function initAdmin() {
  const refreshBtn = $("admin-refresh-btn");
  const exportUsersBtn = $("admin-export-users-btn");
  const exportResumesBtn = $("admin-export-resumes-btn");
  const exportActivityBtn = $("admin-export-activity-btn");

  refreshBtn?.addEventListener("click", () =>
    withButtonLoading(refreshBtn, "Refreshing...", async () => {
      await refreshAdminData();
      showBanner($("global-banner"), "Admin data refreshed.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );

  exportUsersBtn?.addEventListener("click", () =>
    withButtonLoading(exportUsersBtn, "Exporting...", async () => {
      await exportCsv("/api/admin/export/users.csv", "admin-users.csv");
      showBanner($("global-banner"), "Users CSV exported.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );

  exportResumesBtn?.addEventListener("click", () =>
    withButtonLoading(exportResumesBtn, "Exporting...", async () => {
      await exportCsv("/api/admin/export/resumes.csv", "admin-resumes.csv");
      showBanner($("global-banner"), "Resumes CSV exported.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );

  exportActivityBtn?.addEventListener("click", () =>
    withButtonLoading(exportActivityBtn, "Exporting...", async () => {
      await exportCsv("/api/admin/export/activity.csv", "admin-activity.csv");
      showBanner($("global-banner"), "Activity CSV exported.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );
}
