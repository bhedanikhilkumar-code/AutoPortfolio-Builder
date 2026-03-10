import { getDashboard, githubStart, googleAccessTokenLogin, googleConfig, login, logout, register, resendVerificationEmail, verificationStatus } from "./api.js";
import { defaultAfterLoginRoute, navigate, refreshRouterUI } from "./router.js";
import { clearClientAuthState, setState, setToken, state } from "./state.js";
import { $, showBanner, validEmail, withButtonLoading } from "./utils.js";

function globalBanner() {
  return $("global-banner");
}

async function syncUserFromToken() {
  setState({ authReady: false });
  if (!state.token) {
    setState({ user: null, authReady: true });
    refreshRouterUI();
    return;
  }
  try {
    const dashboard = await getDashboard();
    setState({ user: dashboard.user, dashboardData: dashboard });
  } catch {
    clearClientAuthState();
  } finally {
    setState({ authReady: true });
  }
  refreshRouterUI();
}

function ensureCredentials(email, password) {
  if (!validEmail(email)) throw new Error("Enter a valid email.");
  if (!password || password.length < 8) throw new Error("Password must be at least 8 characters.");
}

function disableGoogleAutoSignIn() {
  try {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
      window.google.accounts.id.cancel();
    }
  } catch {
    // best effort
  }
}

function clearTransientInputState() {
  const ids = [
    "login-email",
    "login-password",
    "signup-name",
    "signup-email",
    "signup-password",
    "gen-name",
    "gen-email",
    "gen-github",
    "gen-linkedin",
    "gen-skills",
    "gen-projects",
  ];
  ids.forEach((id) => {
    const el = $(id);
    if (el) el.value = "";
  });
}

async function fetchGoogleUserPhoto(accessToken) {
  try {
    const response = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) return "";
    const payload = await response.json();
    return String(payload?.picture || "").trim();
  } catch {
    return "";
  }
}

async function completeGoogleAccessTokenLogin(accessToken) {
  const [payload, googlePhoto] = await Promise.all([
    googleAccessTokenLogin(accessToken),
    fetchGoogleUserPhoto(accessToken),
  ]);

  setToken(payload.access_token);
  await syncUserFromToken();

  if (googlePhoto) {
    setState({
      user: {
        ...(state.user || {}),
        avatar_url: googlePhoto,
        photo_url: googlePhoto,
        photoURL: googlePhoto,
      },
    });
  }
}

async function startGoogleChooser(prompt = "select_account") {
  const config = await googleConfig();
  if (!config.enabled || !config.client_id || !window.google?.accounts?.oauth2) {
    return false;
  }

  await new Promise((resolve, reject) => {
    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: config.client_id,
      scope: "openid email profile",
      callback: async (response) => {
        try {
          if (response?.error || !response?.access_token) {
            reject(new Error("Google account selection was cancelled or failed."));
            return;
          }
          await completeGoogleAccessTokenLogin(response.access_token);
          resolve();
        } catch (error) {
          reject(error);
        }
      },
    });
    client.requestAccessToken({ prompt });
  });
  return true;
}

export async function performLogout({ redirectTo = "/login", announce = true } = {}) {
  if (state.token) {
    await logout();
  }
  disableGoogleAutoSignIn();
  clearClientAuthState();
  clearTransientInputState();
  refreshRouterUI();
  if (announce) {
    showBanner(globalBanner(), "Logged out. Please sign in manually next time.", "success");
  }
  if (redirectTo) {
    navigate(redirectTo);
  }
}

export async function switchAccount() {
  await performLogout({ redirectTo: null, announce: false });
  try {
    const startedGoogle = await startGoogleChooser("select_account");
    if (startedGoogle) {
      showBanner(globalBanner(), "Switched account successfully.", "success");
      navigate("/");
      return;
    }
  } catch (error) {
    showBanner(globalBanner(), error.message || "Switch account failed.", "error");
  }

  navigate("/login");
  showBanner(globalBanner(), "Signed out. Choose another account to continue.", "info");
}

let signupVerificationEmail = "";
let signupResendCooldownUntil = 0;
let loginVerificationEmail = "";
let loginResendCooldownUntil = 0;

function updateSignupVerificationUI(message = "") {
  const box = $("signup-verification-box");
  const messageEl = $("signup-verification-message");
  const resendBtn = $("signup-resend-verification-btn");
  if (!box || !messageEl || !resendBtn) return;

  const now = Date.now();
  const remainingSec = Math.max(0, Math.ceil((signupResendCooldownUntil - now) / 1000));
  if (remainingSec > 0) {
    resendBtn.disabled = true;
    resendBtn.textContent = `Resend in ${remainingSec}s`;
    window.setTimeout(() => updateSignupVerificationUI(messageEl.textContent), 1000);
  } else {
    resendBtn.disabled = false;
    resendBtn.textContent = "Resend Verification Email";
  }

  if (message) messageEl.textContent = message;
  box.hidden = false;
}

function hideSignupVerificationUI() {
  const box = $("signup-verification-box");
  if (box) box.hidden = true;
}

function updateLoginVerificationUI({ message = "", verified = false, show = true } = {}) {
  const box = $("login-verification-box");
  const messageEl = $("login-verification-message");
  const statusEl = $("login-verification-status");
  const resendBtn = $("login-resend-verification-btn");
  if (!box || !messageEl || !statusEl || !resendBtn) return;

  if (!show) {
    box.hidden = true;
    return;
  }

  const now = Date.now();
  const remainingSec = Math.max(0, Math.ceil((loginResendCooldownUntil - now) / 1000));
  if (remainingSec > 0) {
    resendBtn.disabled = true;
    resendBtn.textContent = `Resend in ${remainingSec}s`;
    window.setTimeout(() => updateLoginVerificationUI({ message: messageEl.textContent, verified, show: true }), 1000);
  } else {
    resendBtn.disabled = verified;
    resendBtn.textContent = verified ? "Resend Verification Email" : "Resend Verification Email";
  }

  if (message) messageEl.textContent = message;
  statusEl.textContent = `Status: ${verified ? "Verified" : "Not Verified"}`;
  resendBtn.hidden = verified;
  box.hidden = false;
}

function hideLoginVerificationUI() {
  const box = $("login-verification-box");
  if (box) box.hidden = true;
}

async function checkLoginVerificationStatus() {
  const email = $("login-email")?.value.trim() || "";
  if (!validEmail(email)) {
    hideLoginVerificationUI();
    return;
  }
  const payload = await verificationStatus({ email });
  loginVerificationEmail = email;
  if (payload?.email_verified) {
    updateLoginVerificationUI({ verified: true, message: "Email is verified.", show: true });
  } else {
    updateLoginVerificationUI({ verified: false, message: "Please verify your email before continuing.", show: true });
  }
}

function bindEmailPasswordAuth() {
  hideSignupVerificationUI();
  hideLoginVerificationUI();
  const loginBtn = $("login-btn");
  const loginEmailInput = $("login-email");
  const registerBtn = $("register-btn");
  const signupResendBtn = $("signup-resend-verification-btn");
  const loginResendBtn = $("login-resend-verification-btn");

  loginBtn?.addEventListener("click", () =>
    withButtonLoading(loginBtn, "Logging in...", async () => {
      const email = $("login-email")?.value.trim() || "";
      const password = $("login-password")?.value || "";
      ensureCredentials(email, password);
      const payload = await login({ email, password });
      loginVerificationEmail = email;

      if (payload?.email_verified === false) {
        updateLoginVerificationUI({
          verified: false,
          message: payload?.message || "Please verify your email before continuing.",
          show: true,
        });
        showBanner(globalBanner(), payload?.message || "Please verify your email before continuing.", "info");
        return;
      }

      hideLoginVerificationUI();
      setToken(payload.access_token);
      await syncUserFromToken();
      showBanner(globalBanner(), payload?.message || "Login successful.", "success");
      navigate(defaultAfterLoginRoute(), { replace: true });
    }).catch((error) => showBanner(globalBanner(), error.message, "error"))
  );

  registerBtn?.addEventListener("click", () =>
    withButtonLoading(registerBtn, "Registering...", async () => {
      const name = $("signup-name")?.value.trim() || "";
      const email = $("signup-email")?.value.trim() || "";
      const password = $("signup-password")?.value || "";
      if (!name || name.length < 2) throw new Error("Enter your name.");
      ensureCredentials(email, password);

      const payload = await register({ name, email, password });
      signupVerificationEmail = email;

      if (payload?.email_verified === false) {
        const message = payload?.message || "Verification email sent. Please check your inbox.";
        updateSignupVerificationUI(message);
        showBanner(globalBanner(), message, message.toLowerCase().includes("could not be sent") ? "error" : "success");
        return;
      }

      hideSignupVerificationUI();
      setToken(payload.access_token);
      await syncUserFromToken();
      showBanner(globalBanner(), "Registration successful.", "success");
      navigate(defaultAfterLoginRoute(), { replace: true });
    }).catch((error) => showBanner(globalBanner(), error.message, "error"))
  );

  signupResendBtn?.addEventListener("click", () =>
    withButtonLoading(signupResendBtn, "Sending...", async () => {
      const email = signupVerificationEmail || $("signup-email")?.value.trim() || "";
      if (!validEmail(email)) throw new Error("Enter the signup email to resend verification.");
      const payload = await resendVerificationEmail({ email });
      signupVerificationEmail = email;
      signupResendCooldownUntil = Date.now() + 60_000;
      updateSignupVerificationUI(payload?.message || "Verification email sent successfully.");
      showBanner(globalBanner(), payload?.message || "Verification email sent successfully.", payload?.ok === false ? "error" : "success");
    }).catch((error) => showBanner(globalBanner(), error.message, "error"))
  );

  loginEmailInput?.addEventListener("blur", () => {
    checkLoginVerificationStatus().catch(() => {
      // keep login UX non-blocking
    });
  });

  loginResendBtn?.addEventListener("click", () =>
    withButtonLoading(loginResendBtn, "Sending...", async () => {
      const email = loginVerificationEmail || $("login-email")?.value.trim() || "";
      if (!validEmail(email)) throw new Error("Enter your login email to resend verification.");
      const payload = await resendVerificationEmail({ email });
      loginVerificationEmail = email;
      loginResendCooldownUntil = Date.now() + 60_000;
      updateLoginVerificationUI({
        verified: false,
        message: payload?.message || "Verification email sent successfully.",
        show: true,
      });
      showBanner(globalBanner(), payload?.message || "Verification email sent successfully.", payload?.ok === false ? "error" : "success");
    }).catch((error) => showBanner(globalBanner(), error.message, "error"))
  );
}

function initGoogleButtons() {
  const loginBtn = $("google-login-btn");
  const signupBtn = $("google-signup-btn");

  const trigger = async (button) => {
    await withButtonLoading(button, "Opening Google...", async () => {
      const started = await startGoogleChooser("select_account");
      if (!started) throw new Error("Google login is not configured.");
      showBanner(globalBanner(), "Signed in with Google.", "success");
      navigate(defaultAfterLoginRoute(), { replace: true });
    }).catch((error) => showBanner(globalBanner(), error.message, "error"));
  };

  loginBtn?.addEventListener("click", () => trigger(loginBtn));
  signupBtn?.addEventListener("click", () => trigger(signupBtn));
}

function initGithubButtons() {
  const loginBtn = $("github-login-btn");
  const signupBtn = $("github-signup-btn");

  const start = async (button) => {
    await withButtonLoading(button, "Opening GitHub...", async () => {
      const payload = await githubStart();
      if (!payload.enabled || !payload.auth_url) throw new Error("GitHub login is not configured.");
      window.location.href = payload.auth_url;
    }).catch((error) => showBanner(globalBanner(), error.message, "error"));
  };

  loginBtn?.addEventListener("click", () => start(loginBtn));
  signupBtn?.addEventListener("click", () => start(signupBtn));
}

export async function initAuth() {
  bindEmailPasswordAuth();
  initGoogleButtons();
  initGithubButtons();
  if (!state.token) {
    disableGoogleAutoSignIn();
  }
  await syncUserFromToken();
}

export async function refreshAuthUser() {
  await syncUserFromToken();
}
