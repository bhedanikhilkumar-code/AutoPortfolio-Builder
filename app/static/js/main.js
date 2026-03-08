import { initAccountMenu } from "./account-menu.js";
import { initAdmin, refreshAdminData } from "./admin.js";
import { initAuth } from "./auth.js";
import { initDashboard, loadDashboardData } from "./dashboard.js";
import { initGenerator } from "./generator.js";
import { initRouter, navigate } from "./router.js";
import { isAuthenticated, isAdmin } from "./state.js";
import { $, showBanner, withButtonLoading } from "./utils.js";

function initBuildPortfolioButton() {
  const buildBtn = $("build-portfolio-btn");
  if (!buildBtn) return;

  buildBtn.addEventListener("click", () =>
    withButtonLoading(buildBtn, "Opening...", async () => {
      if (!isAuthenticated()) {
        showBanner($("global-banner"), "Please log in to build your portfolio.", "info");
        navigate("/login");
        return;
      }
      navigate("/generator");
      showBanner($("global-banner"), "Generator ready.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );
}

async function handleRouteChange(route) {
  if (route === "/dashboard" && isAuthenticated()) {
    try {
      await loadDashboardData();
    } catch (error) {
      showBanner($("global-banner"), error.message, "error");
    }
  }

  if (route === "/admin") {
    if (!isAdmin()) {
      showBanner($("global-banner"), "Admin access required.", "error");
      return;
    }
    try {
      await refreshAdminData();
    } catch (error) {
      showBanner($("global-banner"), error.message, "error");
    }
  }
}

async function bootstrap() {
  initBuildPortfolioButton();
  initGenerator();
  initDashboard();
  initAdmin();
  initAccountMenu();
  initRouter((route) => {
    handleRouteChange(route);
  });
  await initAuth();
}

bootstrap().catch((error) => {
  showBanner($("global-banner"), error.message || "App initialization failed.", "error");
});
