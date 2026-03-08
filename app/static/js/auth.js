import { getDashboard, githubStart, googleAccessTokenLogin, googleConfig, login, logout, register } from "./api.js";
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

async function completeGoogleAccessTokenLogin(accessToken) {
  const payload = await googleAccessTokenLogin(accessToken);
  setToken(payload.access_token);
  await syncUserFromToken();
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

function bindEmailPasswordAuth() {
  const loginBtn = $("login-btn");
  const registerBtn = $("register-btn");

  loginBtn?.addEventListener("click", () =>
    withButtonLoading(loginBtn, "Logging in...", async () => {
      const email = $("login-email")?.value.trim() || "";
      const password = $("login-password")?.value || "";
      ensureCredentials(email, password);
      const payload = await login({ email, password });
      setToken(payload.access_token);
      await syncUserFromToken();
      showBanner(globalBanner(), "Login successful.", "success");
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
      setToken(payload.access_token);
      await syncUserFromToken();
      showBanner(globalBanner(), "Registration successful.", "success");
      navigate(defaultAfterLoginRoute(), { replace: true });
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
