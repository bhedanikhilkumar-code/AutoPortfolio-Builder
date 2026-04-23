import { performLogout, refreshAuthUser, switchAccount } from "./auth.js";
import { removeAccountAvatar, uploadAccountAvatar } from "./api.js";
import { navigate } from "./router.js";
import { setState, state, subscribe } from "./state.js";
import { $, showBanner, showToast, withButtonLoading } from "./utils.js";

const CLOSE_ANIMATION_MS = 140;
const MAX_FILE_SIZE = 2 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
let closeTimer = null;

const cropState = {
  image: null,
  zoom: 1,
  minZoom: 1,
  x: 160,
  y: 160,
  dragging: false,
  dragStartX: 0,
  dragStartY: 0,
  imageStartX: 160,
  imageStartY: 160,
};

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
  return user?.custom_avatar_url || user?.photoURL || user?.providerData?.find((p) => p?.photoURL)?.photoURL || user?.social_avatar_url || user?.avatar_url || user?.photo_url || null;
}

function getMenuElements() {
  return { menu: $("account-dropdown"), trigger: $("account-menu-trigger") };
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

function ensureAvatarControls() {
  const settingsBtn = $("account-settings-link");
  if (!settingsBtn) return;
  const accountSection = settingsBtn.closest(".account-section");
  if (!accountSection) return;

  let uploadBtn = $("account-avatar-upload-btn");
  if (!uploadBtn) {
    uploadBtn = document.createElement("button");
    uploadBtn.id = "account-avatar-upload-btn";
    uploadBtn.className = "account-item";
    uploadBtn.type = "button";
    uploadBtn.setAttribute("role", "menuitem");
    uploadBtn.innerHTML = '<span class="account-item-icon">🖼️</span><span>Upload Photo</span>';
    accountSection.insertBefore(uploadBtn, settingsBtn.nextSibling);
  }

  let removeBtn = $("account-avatar-remove-btn");
  if (!removeBtn) {
    removeBtn = document.createElement("button");
    removeBtn.id = "account-avatar-remove-btn";
    removeBtn.className = "account-item";
    removeBtn.type = "button";
    removeBtn.setAttribute("role", "menuitem");
    removeBtn.hidden = true;
    removeBtn.innerHTML = '<span class="account-item-icon">🗑️</span><span>Remove Photo</span>';
    accountSection.insertBefore(removeBtn, uploadBtn.nextSibling);
  }

  let fileInput = $("account-avatar-input");
  if (!fileInput) {
    fileInput = document.createElement("input");
    fileInput.id = "account-avatar-input";
    fileInput.type = "file";
    fileInput.hidden = true;
    fileInput.setAttribute("accept", ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp");
    accountSection.appendChild(fileInput);
  }
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
  const avatarRemoveBtn = $("account-avatar-remove-btn");

  if (panelName) panelName.textContent = user?.name || "Account";
  if (panelEmail) panelEmail.textContent = user?.email || "";
  if (panelLabel) panelLabel.textContent = user?.is_admin ? "Admin account" : "Personal account";
  if (adminItem) adminItem.hidden = !Boolean(user?.is_admin);
  if (avatarRemoveBtn) avatarRemoveBtn.hidden = !Boolean(user?.custom_avatar_url);

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

function getCropEls() {
  return {
    modal: $("avatar-crop-modal"),
    backdrop: $("avatar-crop-backdrop"),
    canvas: $("avatar-crop-canvas"),
    zoom: $("avatar-crop-zoom"),
    save: $("avatar-crop-save"),
    close: $("avatar-crop-close"),
    cancel: $("avatar-crop-cancel"),
  };
}

function drawCropper() {
  const { canvas } = getCropEls();
  if (!canvas || !cropState.image) return;
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  const radius = width / 2;
  const drawW = cropState.image.width * cropState.zoom;
  const drawH = cropState.image.height * cropState.zoom;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f4f8ff";
  ctx.fillRect(0, 0, width, height);

  ctx.save();
  ctx.beginPath();
  ctx.arc(radius, radius, radius - 2, 0, Math.PI * 2);
  ctx.clip();
  ctx.drawImage(cropState.image, cropState.x - drawW / 2, cropState.y - drawH / 2, drawW, drawH);
  ctx.restore();

  ctx.beginPath();
  ctx.arc(radius, radius, radius - 1, 0, Math.PI * 2);
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(18,64,145,0.7)";
  ctx.stroke();
}

function openCropModal() {
  const { modal, backdrop } = getCropEls();
  if (!modal || !backdrop) return;
  modal.hidden = false;
  backdrop.hidden = false;
  requestAnimationFrame(() => {
    modal.classList.add("is-open");
    backdrop.classList.add("is-open");
  });
  drawCropper();
}

function closeCropModal() {
  const { modal, backdrop, zoom } = getCropEls();
  if (!modal || !backdrop) return;
  modal.classList.remove("is-open");
  backdrop.classList.remove("is-open");
  window.setTimeout(() => {
    modal.hidden = true;
    backdrop.hidden = true;
  }, 120);
  cropState.image = null;
  cropState.zoom = 1;
  if (zoom) zoom.value = "1";
}

function clampImagePosition() {
  const { canvas } = getCropEls();
  if (!canvas || !cropState.image) return;
  const halfW = (cropState.image.width * cropState.zoom) / 2;
  const halfH = (cropState.image.height * cropState.zoom) / 2;
  const r = canvas.width / 2;
  cropState.x = Math.min(halfW, Math.max(canvas.width - halfW, cropState.x));
  cropState.y = Math.min(halfH, Math.max(canvas.height - halfH, cropState.y));

  if (halfW < r) cropState.x = canvas.width / 2;
  if (halfH < r) cropState.y = canvas.height / 2;
}

async function fileToImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Could not load image."));
      img.src = reader.result;
    };
    reader.onerror = () => reject(new Error("Could not read image file."));
    reader.readAsDataURL(file);
  });
}

async function startCropFlow(file) {
  const { zoom } = getCropEls();
  const image = await fileToImage(file);
  cropState.image = image;
  cropState.zoom = 1;
  cropState.minZoom = Math.max(320 / image.width, 320 / image.height, 1);
  cropState.zoom = cropState.minZoom;
  cropState.x = 160;
  cropState.y = 160;
  if (zoom) {
    zoom.min = String(cropState.minZoom);
    zoom.max = "4";
    zoom.value = String(cropState.zoom);
  }
  drawCropper();
  openCropModal();
}

async function canvasToBlob() {
  const { canvas } = getCropEls();
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) return reject(new Error("Could not prepare cropped image."));
      resolve(blob);
    }, "image/png", 0.92);
  });
}

function bindCropEvents() {
  const { canvas, zoom, save, close, cancel, backdrop } = getCropEls();
  if (!canvas || !zoom || !save) return;

  zoom.addEventListener("input", () => {
    cropState.zoom = Number(zoom.value || cropState.minZoom);
    clampImagePosition();
    drawCropper();
  });

  const startDrag = (x, y) => {
    cropState.dragging = true;
    cropState.dragStartX = x;
    cropState.dragStartY = y;
    cropState.imageStartX = cropState.x;
    cropState.imageStartY = cropState.y;
    canvas.classList.add("dragging");
  };

  const moveDrag = (x, y) => {
    if (!cropState.dragging) return;
    cropState.x = cropState.imageStartX + (x - cropState.dragStartX);
    cropState.y = cropState.imageStartY + (y - cropState.dragStartY);
    clampImagePosition();
    drawCropper();
  };

  const endDrag = () => {
    cropState.dragging = false;
    canvas.classList.remove("dragging");
  };

  canvas.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    startDrag(e.clientX, e.clientY);
  });
  window.addEventListener("pointermove", (e) => moveDrag(e.clientX, e.clientY));
  window.addEventListener("pointerup", endDrag);

  save.addEventListener("click", () =>
    withButtonLoading(save, "Saving...", async () => {
      const blob = await canvasToBlob();
      const croppedFile = new File([blob], "avatar.png", { type: "image/png" });
      await uploadAccountAvatar(croppedFile);
      await refreshAuthUser();
      showBanner($("global-banner"), "Profile photo updated.", "success");
      showToast("Photo updated", "success");
      closeCropModal();
      closeMenu();
    }).catch((error) => {
      showBanner($("global-banner"), error.message || "Avatar upload failed.", "error");
      showToast(error.message || "Avatar upload failed.", "error");
    })
  );

  [close, cancel, backdrop].forEach((el) => el?.addEventListener("click", closeCropModal));
}

export function initAccountMenu() {
  ensureAvatarControls();

  const trigger = $("account-menu-trigger");
  const dropdown = $("account-dropdown");
  const dashboardLink = $("account-dashboard-link");
  const generateLink = $("account-generate-link");
  const resumesLink = $("account-resumes-link");
  const draftsLink = $("account-drafts-link");
  const settingsLink = $("account-settings-link");
  const adminLink = $("account-admin-link");
  const switchBtn = $("account-switch-btn");
  const avatarUploadBtn = $("account-avatar-upload-btn");
  const avatarRemoveBtn = $("account-avatar-remove-btn");
  const avatarInput = $("account-avatar-input");
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
    setState({ generatorResult: null });
    navigateFromMenu("/generator", "Generator ready for a new portfolio.");
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

  avatarUploadBtn?.addEventListener("click", () => avatarInput?.click());

  avatarInput?.addEventListener("change", async (event) => {
    const file = event?.target?.files?.[0];
    avatarInput.value = "";
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      showBanner($("global-banner"), "Invalid format. Use JPG, JPEG, PNG, or WEBP.", "error");
      showToast("Invalid file type", "error");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      showBanner($("global-banner"), "Image too large. Max size is 2MB.", "error");
      showToast("File too large (max 2MB)", "error");
      return;
    }
    try {
      await startCropFlow(file);
    } catch (error) {
      showBanner($("global-banner"), error.message || "Could not open cropper.", "error");
      showToast(error.message || "Could not open cropper.", "error");
    }
  });

  avatarRemoveBtn?.addEventListener("click", () =>
    withButtonLoading(avatarRemoveBtn, "Removing...", async () => {
      await removeAccountAvatar();
      await refreshAuthUser();
      showBanner($("global-banner"), "Custom profile photo removed.", "success");
      showToast("Custom photo removed", "success");
      closeMenu();
    }).catch((error) => {
      showBanner($("global-banner"), error.message || "Failed to remove photo.", "error");
      showToast(error.message || "Failed to remove photo.", "error");
    })
  );

  logoutBtn?.addEventListener("click", () =>
    withButtonLoading(logoutBtn, "Logging out...", async () => {
      closeMenu();
      await performLogout({ redirectTo: "/login", announce: true });
    })
  );

  bindCropEvents();

  document.addEventListener("click", (event) => {
    const root = $("account-menu");
    if (!root || root.hidden) return;
    if (root.contains(event.target)) return;
    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
      closeCropModal();
    }
  });

  subscribe((nextState) => {
    renderAccountMenu(nextState);
    if (!nextState.token) closeMenu();
  });

  renderAccountMenu(state);
}
