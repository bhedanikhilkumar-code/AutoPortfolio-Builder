export function $(id) {
  return document.getElementById(id);
}

export function showBanner(element, message, level = "info") {
  if (!element) return;
  element.textContent = message;
  element.className = `banner ${level}`;
  element.hidden = false;
}

export function hideBanner(element) {
  if (!element) return;
  element.hidden = true;
  element.textContent = "";
  element.className = "banner";
}

export function setButtonLoading(button, isLoading, loadingText = "Loading...") {
  if (!button) return;
  if (isLoading) {
    if (!button.dataset.originalText) button.dataset.originalText = button.textContent || "";
    button.disabled = true;
    button.textContent = loadingText;
    return;
  }
  button.disabled = false;
  if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
  }
}

export function withButtonLoading(button, loadingText, task) {
  setButtonLoading(button, true, loadingText);
  return Promise.resolve()
    .then(task)
    .finally(() => setButtonLoading(button, false));
}

export function parseApiError(payload, fallback) {
  return payload?.error?.message || payload?.detail || fallback;
}

export function validEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function normalizeGithubInput(value) {
  const raw = value.trim();
  if (!raw) return { ok: false, message: "GitHub is required." };
  if (/^https?:\/\//i.test(raw)) {
    const match = raw.match(/^https?:\/\/(www\.)?github\.com\/([A-Za-z0-9-]+)(?:\/|$)/i);
    if (!match) return { ok: false, message: "Enter a valid GitHub username or profile URL." };
    return { ok: true, value: match[2] };
  }
  if (!/^[A-Za-z0-9-]{1,39}$/.test(raw)) {
    return { ok: false, message: "GitHub username can only include letters, numbers, or hyphens." };
  }
  return { ok: true, value: raw };
}

export function normalizeLinkedInInput(value) {
  const raw = value.trim();
  if (!raw) return { ok: true, value: "" };
  if (/^https?:\/\//i.test(raw)) {
    const match = raw.match(/^https?:\/\/(www\.)?linkedin\.com\/in\/([A-Za-z0-9-]+)\/?/i);
    if (!match) return { ok: false, message: "Enter a valid LinkedIn username or /in/ URL." };
    return { ok: true, value: match[2] };
  }
  if (!/^[A-Za-z0-9-]{3,100}$/.test(raw)) {
    return { ok: false, message: "LinkedIn username can only include letters, numbers, or hyphens." };
  }
  return { ok: true, value: raw };
}

export function splitCsv(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function contentDispositionFilename(headerValue, fallback) {
  const match = headerValue?.match(/filename="([^"]+)"/i);
  return match?.[1] || fallback;
}
