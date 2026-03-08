import { performLogout, switchAccount } from "./auth.js";
import { navigate } from "./router.js";
import { state, subscribe } from "./state.js";
import { $, showBanner, withButtonLoading } from "./utils.js";

const CLOSE_ANIMATION_MS = 140;
let closeTimer = null;

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

function resolveUserPhoto(user) {
  return user?.photoURL || user?.providerData?.find((p) => p?.photoURL)?.photoURL || user?.avatar_url || user?.photo_url || null;
}

function getMenuElements() {
  return {
    menu: $("account-dropdown"),
    trigger: $("account-menu-trigger"),
  };
}

function openMenu() {
  const { menu, trigger } = getMenuElements();
  if (!menu || !trigger) return;
  if (closeTimer) {
    clearTimeout(closeTimer);
    closeTimer = null;
  }

  menu.hidden = false;
  menu.classList.remove("is-closing");
  requestAnimationFrame(() => menu.classList.add("is-open"));
  trigger.setAttribute("aria-expanded", "true");
}

function closeMenu() {
  const { menu, trigger } = getMenuElements();
  if (!menu || !trigger || menu.hidden) return;

  menu.classList.remove("is-open");
  menu.classList.add("is-closing");
  trigger.setAttribute("aria-expanded", "false");

  if (closeTimer) clearTimeout(closeTimer);
  closeTimer = window.setTimeout(() => {
    menu.hidden = true;
    menu.classList.remove("is-closing");
    closeTimer = null;
  }, CLOSE_ANIMATION_MS);
}

function toggleMenu() {
  const { menu } = getMenuElements();
  if (!menu) return;
  if (menu.hidden) openMenu();
  else closeMenu();
}

function navigateFromMenu(path, message = "") {
  closeMenu();
  navigate(path);
  if (message) showBanner($("global-banner"), message, "info");
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
  const panelLabel = $("account-panel-label");
  const adminItem = $("account-admin-link");

  if (panelName) panelName.textContent = user?.name || "Account";
  if (panelEmail) panelEmail.textContent = user?.email || "";
  if (panelLabel) panelLabel.textContent = user?.is_admin ? "Admin account" : "Personal account";
  if (adminItem) adminItem.hidden = !Boolean(user?.is_admin);

  const avatarUrl = resolveUserPhoto(user);
  const hasPhoto = Boolean(avatarUrl);

  if (triggerFallback) triggerFallback.textContent = initials;
  if (panelFallback) panelFallback.textContent = initials;

  if (triggerImage) {
    triggerImage.hidden = !hasPhoto;
    if (hasPhoto) triggerImage.src = avatarUrl;
    else triggerImage.removeAttribute("src");
  }
  if (panelImage) {
    panelImage.hidden = !hasPhoto;
    if (hasPhoto) panelImage.src = avatarUrl;
    else panelImage.removeAttribute("src");
  }

  if (triggerFallback) triggerFallback.hidden = hasPhoto;
  if (panelFallback) panelFallback.hidden = hasPhoto;
}

export function initAccountMenu() {
  const trigger = $("account-menu-trigger");
  const dropdown = $("account-dropdown");

  const dashboardLink = $("account-dashboard-link");
  const generateLink = $("account-generate-link");
  const resumesLink = $("account-resumes-link");
  const draftsLink = $("account-drafts-link");
  const settingsLink = $("account-settings-link");
  const adminLink = $("account-admin-link");
  const switchBtn = $("account-switch-btn");
  const logoutBtn = $("account-logout-btn");

  if (!trigger || !dropdown) return;

  trigger.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleMenu();
  });

  dashboardLink?.addEventListener("click", (event) => {
    event.preventDefault();
    navigateFromMenu("/dashboard");
  });

  generateLink?.addEventListener("click", (event) => {
    event.preventDefault();
    navigateFromMenu("/generator");
  });

  resumesLink?.addEventListener("click", (event) => {
    event.preventDefault();
    navigateFromMenu("/dashboard", "Tip: Use your dashboard to manage resumes.");
  });

  draftsLink?.addEventListener("click", (event) => {
    event.preventDefault();
    navigateFromMenu("/dashboard", "Tip: Saved drafts are available in dashboard.");
  });

  settingsLink?.addEventListener("click", (event) => {
    event.preventDefault();
    navigateFromMenu("/dashboard", "Account settings are available in dashboard.");
  });

  adminLink?.addEventListener("click", (event) => {
    event.preventDefault();
    navigateFromMenu("/admin");
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
