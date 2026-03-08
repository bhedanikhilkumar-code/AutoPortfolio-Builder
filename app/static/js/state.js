const listeners = new Set();
const TOKEN_KEY = "apb_token";

function readStoredToken() {
  const localToken = localStorage.getItem(TOKEN_KEY);
  if (localToken) return localToken;

  const legacySessionToken = sessionStorage.getItem(TOKEN_KEY);
  if (legacySessionToken) {
    localStorage.setItem(TOKEN_KEY, legacySessionToken);
    return legacySessionToken;
  }
  return "";
}

export const state = {
  token: readStoredToken(),
  user: null,
  pendingRoute: "/",
  generatorResult: null,
  dashboardData: null,
  adminData: null,
  authReady: false,
};

export function setState(patch) {
  Object.assign(state, patch);
  listeners.forEach((listener) => listener(state));
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
  }
  setState({ token: token || "" });
}

export function clearClientAuthState() {
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_KEY);
  setState({
    token: "",
    user: null,
    pendingRoute: "/",
    generatorResult: null,
    dashboardData: null,
    adminData: null,
  });
}

export function isAuthenticated() {
  return Boolean(state.token);
}

export function isAdmin() {
  return Boolean(state.user?.is_admin);
}
