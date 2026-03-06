import { getDashboard } from "./api.js";
import { state } from "./state.js";
import { $, showBanner, withButtonLoading } from "./utils.js";

function renderDashboard(data) {
  const root = $("dashboard-content");
  if (!root) return;
  const resumes = (data.my_resumes || []).map((item) => `<li>${item.title} (${item.status})</li>`).join("") || "<li>No resumes yet.</li>";
  const drafts = (data.saved_drafts || []).map((item) => `<li>${item.title}</li>`).join("") || "<li>No drafts yet.</li>";
  const history = (data.generation_history || []).map((item) => `<li>${item.username} · variant ${item.variant_id}</li>`).join("") || "<li>No generation history.</li>";

  root.innerHTML = `
    <section>
      <h3>Account</h3>
      <p>${data.user.email} ${data.user.is_admin ? "(admin)" : ""}</p>
    </section>
    <section>
      <h3>My Resumes</h3>
      <ul>${resumes}</ul>
    </section>
    <section>
      <h3>Saved Drafts</h3>
      <ul>${drafts}</ul>
    </section>
    <section>
      <h3>Generation History</h3>
      <ul>${history}</ul>
    </section>
  `;
}

export async function loadDashboardData() {
  const data = await getDashboard();
  renderDashboard(data);
  return data;
}

export function initDashboard() {
  const loadBtn = $("load-dashboard-btn");
  loadBtn?.addEventListener("click", () =>
    withButtonLoading(loadBtn, "Loading...", async () => {
      if (!state.token) throw new Error("Login required.");
      const data = await loadDashboardData();
      showBanner($("global-banner"), "Dashboard loaded.", "success");
      return data;
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );
}
