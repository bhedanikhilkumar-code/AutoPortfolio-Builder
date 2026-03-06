const listeners = new Set();
const TOKEN_KEY = "apb_token";

function readStoredToken() {
  const sessionToken = sessionStorage.getItem(TOKEN_KEY);
  if (sessionToken) return sessionToken;

  const legacyLocalToken = localStorage.getItem(TOKEN_KEY);
  if (legacyLocalToken) {
    sessionStorage.setItem(TOKEN_KEY, legacyLocalToken);
    localStorage.removeItem(TOKEN_KEY);
    return legacyLocalToken;
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
    sessionStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(TOKEN_KEY);
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
