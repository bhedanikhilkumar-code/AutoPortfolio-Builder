export function $(id) {
  return document.getElementById(id);
}

export function showBanner(element, message, level = "info") {
  if (!element) return;
  element.textContent = message;
  element.className = `banner ${level}`;
  element.hidden = false;
}

export function showToast(message, level = "info", timeoutMs = 2600) {
  if (!message) return;
  let stack = document.getElementById("toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.id = "toast-stack";
    stack.className = "toast-stack";
    document.body.appendChild(stack);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${level}`;
  toast.textContent = message;
  stack.appendChild(toast);
  window.setTimeout(() => toast.remove(), timeoutMs);
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

export function meaningfulText(value, { minLetters = 3, minUniqueLetters = 3 } = {}) {
  const text = (value || "").trim();
  if (text.length < minLetters) return false;
  const letters = (text.match(/[A-Za-z]/g) || []);
  if (letters.length < minLetters) return false;
  if (new Set(letters.map((x) => x.toLowerCase())).size < minUniqueLetters) return false;

  const lower = text.toLowerCase();
  const garbagePatterns = ["asdf", "qwer", "zxcv", "sdfg", "poiuy", "lkjh", "testtest", "random"];
  if (garbagePatterns.some((p) => lower.includes(p))) return false;

  if (/^[A-Za-z]{5,}$/.test(text) && !/[aeiou]/i.test(text)) return false;
  if (/^[A-Za-z0-9]{7,}$/.test(text) && !/[\s]/.test(text) && !/[aeiou]/i.test(text)) return false;

  const vowelCount = (text.match(/[aeiou]/gi) || []).length;
  if (letters.length >= 6 && vowelCount === 0) return false;
  if (letters.length >= 8 && vowelCount <= 1) return false;

  return true;
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
  if (!raw) return { ok: true, value: "", profileUrl: "" };

  const normalized = raw.replace(/^@/, "").trim();

  // Accept full URL with/without protocol: linkedin.com/in/username
  const urlLike = normalized.match(/^(?:https?:\/\/)?(?:[a-z]{2,3}\.)?(?:www\.)?linkedin\.com\/in\/([A-Za-z0-9-]{3,100})(?:[\/?#].*)?$/i);
  if (urlLike) {
    const username = urlLike[1];
    return { ok: true, value: username, profileUrl: `https://www.linkedin.com/in/${username}` };
  }

  // Accept bare username
  if (/^[A-Za-z0-9-]{3,100}$/.test(normalized)) {
    return { ok: true, value: normalized, profileUrl: `https://www.linkedin.com/in/${normalized}` };
  }

  return {
    ok: false,
    message: "Enter a valid LinkedIn username or profile URL (linkedin.com/in/username).",
  };
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
  anchor.rel = "noopener";
  anchor.target = "_blank";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 3000);
}

export function contentDispositionFilename(headerValue, fallback) {
  const match = headerValue?.match(/filename="([^"]+)"/i);
  return match?.[1] || fallback;
}
