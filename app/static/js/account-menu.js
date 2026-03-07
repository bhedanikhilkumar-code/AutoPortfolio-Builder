import { performLogout, switchAccount } from "./auth.js";
import { navigate } from "./router.js";
import { state, subscribe } from "./state.js";
import { $, withButtonLoading } from "./utils.js";

function initialsFromUser(user) {
  const name = (user?.name || "").trim();
  if (name) {
    const tokens = name.split(/\s+/).filter(Boolean);
    const first = tokens[0]?.[0] || "";
    const second = tokens[1]?.[0] || "";
    return (first + second).toUpperCase();
  }
  const email = (user?.email || "").trim();
  return (email[0] || "U").toUpperCase();
}

function openMenu() {
  const menu = $("account-dropdown");
  const trigger = $("account-menu-trigger");
  if (!menu || !trigger) return;
  menu.hidden = false;
  trigger.setAttribute("aria-expanded", "true");
}

function closeMenu() {
  const menu = $("account-dropdown");
  const trigger = $("account-menu-trigger");
  if (!menu || !trigger) return;
  menu.hidden = true;
  trigger.setAttribute("aria-expanded", "false");
}

function toggleMenu() {
  const menu = $("account-dropdown");
  if (!menu) return;
  if (menu.hidden) openMenu();
  else closeMenu();
}

function renderAccountMenu(nextState = state) {
  const user = nextState.user;
  const initials = initialsFromUser(user);

  const triggerFallback = $("account-avatar-fallback");
  const triggerImage = $("account-avatar-img");
  const panelFallback = $("account-panel-avatar-fallback");
  const panelImage = $("account-panel-avatar-img");
  const panelName = $("account-panel-name");
  const panelEmail = $("account-panel-email");

  if (panelName) panelName.textContent = user?.name || "Account";
  if (panelEmail) panelEmail.textContent = user?.email || "";

  const avatarUrl = user?.avatar_url || "";
  const hasPhoto = Boolean(avatarUrl);

  if (triggerFallback) triggerFallback.textContent = initials;
  if (panelFallback) panelFallback.textContent = initials;

  if (triggerImage) {
    triggerImage.hidden = !hasPhoto;
    if (hasPhoto) triggerImage.src = avatarUrl;
  }
  if (panelImage) {
    panelImage.hidden = !hasPhoto;
    if (hasPhoto) panelImage.src = avatarUrl;
  }

  if (triggerFallback) triggerFallback.hidden = hasPhoto;
  if (panelFallback) panelFallback.hidden = hasPhoto;
}

export function initAccountMenu() {
  const trigger = $("account-menu-trigger");
  const dropdown = $("account-dropdown");
  const dashboardLink = $("account-dashboard-link");
  const resumesLink = $("account-resumes-link");
  const switchBtn = $("account-switch-btn");
  const logoutBtn = $("account-logout-btn");

  if (!trigger || !dropdown) return;

  trigger.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleMenu();
  });

  dashboardLink?.addEventListener("click", (event) => {
    event.preventDefault();
    closeMenu();
    navigate("/dashboard");
  });

  resumesLink?.addEventListener("click", (event) => {
    event.preventDefault();
    closeMenu();
    navigate("/dashboard");
  });

  switchBtn?.addEventListener("click", () =>
    withButtonLoading(switchBtn, "Switching...", async () => {
      closeMenu();
      await switchAccount();
    })
  );

  logoutBtn?.addEventListener("click", () =>
    withButtonLoading(logoutBtn, "Logging out...", async () => {
      closeMenu();
      await performLogout({ redirectTo: "/login", announce: true });
    })
  );

  document.addEventListener("click", (event) => {
    const root = $("account-menu");
    if (!root || root.hidden) return;
    if (root.contains(event.target)) return;
    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });

  subscribe((nextState) => {
    renderAccountMenu(nextState);
    if (!nextState.token) closeMenu();
  });

  renderAccountMenu(state);
}
