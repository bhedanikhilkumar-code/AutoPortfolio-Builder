import { getDashboard, githubStart, googleConfig, googleLogin, login, logout, register } from "./api.js";
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
      navigate(defaultAfterLoginRoute());
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
      navigate(defaultAfterLoginRoute());
    }).catch((error) => showBanner(globalBanner(), error.message, "error"))
  );
}

async function handleGoogleCredentialResponse(response) {
  if (!response?.credential) {
    throw new Error("Google credential missing.");
  }
  const payload = await googleLogin(response.credential);
  setToken(payload.access_token);
  await syncUserFromToken();
  showBanner(globalBanner(), "Signed in with Google.", "success");
  navigate(defaultAfterLoginRoute());
}

function initGoogleButtons() {
  const loginBtn = $("google-login-btn");
  const signupBtn = $("google-signup-btn");

  const trigger = async (button) => {
    await withButtonLoading(button, "Opening Google...", async () => {
      const config = await googleConfig();
      if (!config.enabled || !config.client_id) throw new Error("Google login is not configured.");
      if (!window.google?.accounts?.id) throw new Error("Google script not available. Refresh and try again.");

      window.google.accounts.id.initialize({
        client_id: config.client_id,
        auto_select: false,
        callback: async (credentialResponse) => {
          try {
            await handleGoogleCredentialResponse(credentialResponse);
          } catch (error) {
            showBanner(globalBanner(), error.message, "error");
          }
        },
      });

      // Manual-only login: never render Google's personalized account button in-page.
      // Start chooser only after explicit click.
      window.google.accounts.id.prompt();
      showBanner(globalBanner(), "Continue in the Google account chooser.", "info");
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

function initLogout() {
  const logoutBtn = $("logout-btn");
  logoutBtn?.addEventListener("click", () =>
    withButtonLoading(logoutBtn, "Logging out...", async () => {
      if (state.token) {
        await logout();
      }
      disableGoogleAutoSignIn();
      clearClientAuthState();
      refreshRouterUI();
      showBanner(globalBanner(), "Logged out. Please sign in manually next time.", "success");
      navigate("/login");
    }).catch((error) => showBanner(globalBanner(), error.message, "error"))
  );
}

export async function initAuth() {
  bindEmailPasswordAuth();
  initGoogleButtons();
  initGithubButtons();
  initLogout();
  if (!state.token) {
    disableGoogleAutoSignIn();
  }
  await syncUserFromToken();
}

export async function refreshAuthUser() {
  await syncUserFromToken();
}
