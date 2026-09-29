let memoryToken = "";

export function setToken(token) {
  memoryToken = token || "";
}

export function hasToken() {
  return memoryToken.length > 0;
}

export async function api(path, options = {}) {
  const headers = { Accept: "application/json" };
  if (options.body) headers["Content-Type"] = "application/json";
  if (memoryToken) headers.Authorization = "Bearer " + memoryToken;
  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (response.status === 204) return null;
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (_error) {
      payload = null;
    }
  }
  if (!response.ok) {
    let message = "Request failed";
    if (payload && typeof payload.detail === "string") message = payload.detail;
    else if (payload && Array.isArray(payload.detail)) {
      message = payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
    }
    const error = new Error(message || "Request failed");
    error.status = response.status;
    throw error;
  }
  return payload;
}
