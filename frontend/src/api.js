const KEY = "tracker_api_key";

export function getApiKey() {
  return sessionStorage.getItem(KEY) || "";
}

export function setApiKey(value) {
  sessionStorage.setItem(KEY, value);
}

export function clearApiKey() {
  sessionStorage.removeItem(KEY);
}

export async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Api-Key": getApiKey(),
    ...(options.headers || {}),
  };
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    clearApiKey();
    const err = new Error("unauthorized");
    err.status = 401;
    throw err;
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return null;
  return response.json();
}
