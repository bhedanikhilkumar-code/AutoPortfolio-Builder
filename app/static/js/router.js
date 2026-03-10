import { isAdmin, isAuthenticated, state } from "./state.js";
import { $, showBanner } from "./utils.js";

const ROUTES = ["/", "/login", "/signup", "/dashboard", "/generator", "/admin", "/auth-loading"];
const PRIVATE_ROUTES = new Set(["/dashboard", "/generator", "/admin"]);
const PUBLIC_ONLY_ROUTES = new Set(["/login", "/signup"]);

let onRoute = null;

function normalizeRoute(pathname = window.location.pathname) {
  if (!pathname) return "/";
  const withoutTrailingSlash = pathname !== "/" ? pathname.replace(/\/+$/, "") : "/";
  return ROUTES.includes(withoutTrailingSlash) ? withoutTrailingSlash : "/";
}

function syncLegacyHashRoute() {
  const hash = window.location.hash || "";
  if (!hash.startsWith("#/")) return;
  const legacyRoute = normalizeRoute(hash.slice(1));
  window.history.replaceState({}, "", legacyRoute);
}

export function currentRoute() {
  syncLegacyHashRoute();
  return normalizeRoute();
}

export function navigate(route, { replace = false } = {}) {
  const next = normalizeRoute(route);
  if (window.location.pathname === next) {
    handleRoute();
    return;
  }
  if (replace) {
    window.history.replaceState({}, "", next);
  } else {
    window.history.pushState({}, "", next);
  }
  handleRoute();
}

function applyNavVisibility() {
  const authReady = Boolean(state.authReady);
  const route = currentRoute();
  const onLanding = route === "/";
  const isVerifiedUser = Boolean(state.user?.email_verified !== false);

  document.querySelectorAll("[data-auth-only]").forEach((node) => {
    node.hidden = !authReady || !isAuthenticated() || !isVerifiedUser || onLanding;
  });
  document.querySelectorAll("[data-admin-only]").forEach((node) => {
    node.hidden = !authReady || !isAuthenticated() || !isVerifiedUser || !isAdmin() || onLanding;
  });
  document.querySelectorAll("[data-guest-only]").forEach((node) => {
    node.hidden = !authReady || (!onLanding && isAuthenticated() && isVerifiedUser);
  });
  const accountMenu = $("account-menu");
  if (accountMenu) accountMenu.hidden = !authReady || !isAuthenticated() || !isVerifiedUser || onLanding;
}

function routeGuard(route) {
  if (PRIVATE_ROUTES.has(route) && !isAuthenticated()) {
    state.pendingRoute = route;
    navigate("/login", { replace: true });
    showBanner($("global-banner"), "Login required to access that page.", "info");
    return false;
  }
  if (PRIVATE_ROUTES.has(route) && isAuthenticated() && state.user?.email_verified === false) {
    navigate("/login", { replace: true });
    showBanner($("global-banner"), "Please verify your email before continuing.", "info");
    return false;
  }
  if (PUBLIC_ONLY_ROUTES.has(route) && isAuthenticated() && state.user?.email_verified !== false) {
    navigate("/dashboard", { replace: true });
    showBanner($("global-banner"), "You are already logged in.", "info");
    return false;
  }
  if (route === "/admin" && (!isAuthenticated() || !isAdmin())) {
    navigate(isAuthenticated() ? "/dashboard" : "/login", { replace: true });
    showBanner($("global-banner"), "Admin access required.", "error");
    return false;
  }
  return true;
}

function renderRoute(route) {
  document.querySelectorAll(".view").forEach((view) => {
    const isActive = view.dataset.route === route;
    view.hidden = !isActive;
    view.style.display = isActive ? "block" : "none";
  });
}

function handleLinkClicks(event) {
  const anchor = event.target.closest("a[href]");
  if (!anchor) return;
  const href = anchor.getAttribute("href") || "";
  if (!href.startsWith("/")) return;
  if (anchor.target && anchor.target !== "_self") return;
  event.preventDefault();
  navigate(href);
}

function updateActiveNav(route) {
  document.querySelectorAll("#main-nav a[href^='/']").forEach((link) => {
    const href = link.getAttribute("href") || "/";
    const isActive = route === href;
    link.classList.toggle("is-active", isActive);
    if (isActive) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

function handleRoute() {
  const route = currentRoute();
  applyNavVisibility();
  updateActiveNav(route);
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
  window.addEventListener("popstate", handleRoute);
  document.addEventListener("click", handleLinkClicks);
  handleRoute();
}

export function refreshRouterUI() {
  applyNavVisibility();
  handleRoute();
}

export function defaultAfterLoginRoute() {
  return state.pendingRoute && PRIVATE_ROUTES.has(state.pendingRoute) ? state.pendingRoute : "/dashboard";
}
