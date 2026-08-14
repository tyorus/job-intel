const STORAGE_KEY = "tracker_theme";

export function resolveTheme(preference) {
  if (preference === "light" || preference === "dark") return preference;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function getStoredTheme() {
  return localStorage.getItem(STORAGE_KEY) || "system";
}

export function applyTheme(preference = getStoredTheme()) {
  const resolved = resolveTheme(preference);
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
  return resolved;
}

export function setThemePreference(preference) {
  localStorage.setItem(STORAGE_KEY, preference);
  return applyTheme(preference);
}

export function cycleTheme(currentPreference = getStoredTheme()) {
  const order = ["system", "light", "dark"];
  const next = order[(order.indexOf(currentPreference) + 1) % order.length];
  return { preference: next, resolved: setThemePreference(next) };
}
