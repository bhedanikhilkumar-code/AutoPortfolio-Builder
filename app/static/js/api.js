import { state } from "./state.js";
import { parseApiError } from "./utils.js";

async function parseResponse(response, fallbackMessage) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : { detail: await response.text() };
  if (!response.ok) {
    throw new Error(parseApiError(payload, fallbackMessage));
  }
  return payload;
}

function authHeaders() {
  if (!state.token) return {};
  return { Authorization: `Bearer ${state.token}` };
}

export async function getDashboard() {
  const response = await fetch("/api/dashboard", { headers: { ...authHeaders() } });
  return parseResponse(response, "Failed to load dashboard.");
}

export async function register(payload) {
  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Registration failed.");
}

export async function login(payload) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Login failed.");
}

export async function logout() {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
    headers: { ...authHeaders() },
  });
  return parseResponse(response, "Logout failed.");
}

export async function googleConfig() {
  const response = await fetch("/api/auth/google/config");
  return parseResponse(response, "Google Sign-In config failed.");
}

export async function googleLogin(idToken) {
  const response = await fetch("/api/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  return parseResponse(response, "Google login failed.");
}

export async function googleStart() {
  const response = await fetch("/api/auth/google/start");
  return parseResponse(response, "Google login is not available.");
}

export async function googleAccessTokenLogin(accessToken) {
  const response = await fetch("/api/auth/google/access-token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  });
  return parseResponse(response, "Google login failed.");
}

export async function githubStart() {
  const response = await fetch("/api/auth/github/start");
  return parseResponse(response, "GitHub login is not available.");
}

export async function fetchProfile(payload) {
  const response = await fetch("/api/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Profile fetch failed.");
}

export async function generatePortfolio(payload) {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Portfolio generation failed.");
}

export async function getAdminStats() {
  const response = await fetch("/api/admin/stats", { headers: { ...authHeaders() } });
  return parseResponse(response, "Admin stats failed.");
}

export async function getAdminUsers() {
  const response = await fetch("/api/admin/users", { headers: { ...authHeaders() } });
  return parseResponse(response, "Admin users failed.");
}

export async function getAdminResumes() {
  const response = await fetch("/api/admin/resumes", { headers: { ...authHeaders() } });
  return parseResponse(response, "Admin resumes failed.");
}

export async function getAdminActivity() {
  const response = await fetch("/api/admin/activity", { headers: { ...authHeaders() } });
  return parseResponse(response, "Admin activity failed.");
}

export async function exportAdminCsv(path) {
  const response = await fetch(path, { headers: { ...authHeaders() } });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : { detail: await response.text() };
    throw new Error(parseApiError(payload, "CSV export failed."));
  }
  return response;
}

export async function uploadAccountAvatar(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/account/avatar", {
    method: "POST",
    headers: { ...authHeaders() },
    body: form,
  });
  return parseResponse(response, "Avatar upload failed.");
}

export async function removeAccountAvatar() {
  const response = await fetch("/api/account/avatar", {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  return parseResponse(response, "Failed to remove avatar.");
}

export async function saveResume(payload) {
  const response = await fetch("/api/dashboard/resumes", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Failed to save resume.");
}

export async function getResume(resumeId) {
  const response = await fetch(`/api/dashboard/resumes/${resumeId}`, {
    headers: { ...authHeaders() },
  });
  return parseResponse(response, "Failed to load resume.");
}

export async function duplicateResume(resumeId) {
  const response = await fetch(`/api/dashboard/resumes/${resumeId}/duplicate`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  return parseResponse(response, "Failed to duplicate resume.");
}

export async function deleteResume(resumeId) {
  const response = await fetch(`/api/dashboard/resumes/${resumeId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  return parseResponse(response, "Failed to delete resume.");
}

export async function exportPortfolio(format, payload) {
  const response = await fetch(`/api/export/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const err = contentType.includes("application/json") ? await response.json() : { detail: await response.text() };
    throw new Error(parseApiError(err, `Export ${format.toUpperCase()} failed.`));
  }
  return response;
}
