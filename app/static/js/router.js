import { isAdmin, isAuthenticated, state } from "./state.js";
import { $, showBanner } from "./utils.js";

const ROUTES = ["/", "/login", "/signup", "/dashboard", "/generator", "/admin", "/auth-loading"];
const PRIVATE_ROUTES = new Set(["/dashboard", "/generator", "/admin"]);

let onRoute = null;

export function currentRoute() {
  const hash = window.location.hash || "#/";
  const route = hash.replace(/^#/, "") || "/";
  return ROUTES.includes(route) ? route : "/";
}

export function navigate(route) {
  const next = ROUTES.includes(route) ? route : "/";
  window.location.hash = `#${next}`;
}

function applyNavVisibility() {
  const authReady = Boolean(state.authReady);
  document.querySelectorAll("[data-auth-only]").forEach((node) => {
    node.hidden = !authReady || !isAuthenticated();
  });
  document.querySelectorAll("[data-admin-only]").forEach((node) => {
    node.hidden = !authReady || !isAuthenticated() || !isAdmin();
  });
  document.querySelectorAll("[data-guest-only]").forEach((node) => {
    node.hidden = !authReady || isAuthenticated();
  });
  const logoutBtn = $("logout-btn");
  if (logoutBtn) logoutBtn.hidden = !authReady || !isAuthenticated();
}

function routeGuard(route) {
  if (PRIVATE_ROUTES.has(route) && !isAuthenticated()) {
    state.pendingRoute = route;
    navigate("/login");
    showBanner($("global-banner"), "Login required to access that page.", "info");
    return false;
  }
  if (route === "/admin" && (!isAuthenticated() || !isAdmin())) {
    navigate(isAuthenticated() ? "/dashboard" : "/login");
    showBanner($("global-banner"), "Admin access required.", "error");
    return false;
  }
  return true;
}

function renderRoute(route) {
  document.querySelectorAll(".view").forEach((view) => {
    view.hidden = view.dataset.route !== route;
  });
}

function handleRoute() {
  const route = currentRoute();
  applyNavVisibility();
  if (!state.authReady) {
    renderRoute("/auth-loading");
    return;
  }
  if (!routeGuard(route)) return;
  renderRoute(route);
  if (onRoute) onRoute(route);
}

export function initRouter(routeHandler) {
  onRoute = routeHandler;
  window.addEventListener("hashchange", handleRoute);
  handleRoute();
}

export function refreshRouterUI() {
  applyNavVisibility();
  handleRoute();
}

export function defaultAfterLoginRoute() {
  return state.pendingRoute && PRIVATE_ROUTES.has(state.pendingRoute) ? state.pendingRoute : "/dashboard";
}
