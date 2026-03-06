const listeners = new Set();

export const state = {
  token: localStorage.getItem("apb_token") || "",
  user: null,
  pendingRoute: "/",
  generatorResult: null,
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
    localStorage.setItem("apb_token", token);
  } else {
    localStorage.removeItem("apb_token");
  }
  setState({ token: token || "" });
}

export function isAuthenticated() {
  return Boolean(state.token);
}

export function isAdmin() {
  return Boolean(state.user?.is_admin);
}
