import { API_BASE_URL } from "../config/api.js";

async function getErrorMessage(response) {
  const text = await response.text();
  try {
    const payload = JSON.parse(text);
    if (typeof payload?.error === "string") return payload.error;
    if (typeof payload?.error?.message === "string") return payload.error.message;
    if (typeof payload?.message === "string") return payload.message;
  } catch {
    // Non-JSON responses are handled below.
  }

  const contentType = response.headers?.get?.("content-type") || "";
  const isHtml = contentType.includes("text/html") || /^\s*(?:<!doctype\s+html|<html)/i.test(text);
  if (isHtml) {
    return `API 请求失败（${response.status}）：服务器返回了 HTML 页面，请检查 Nginx /api/ 反向代理配置。`;
  }
  return text || `API 请求失败（${response.status}）`;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function downloadFilename(disposition, fallback) {
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded);
    } catch {
      return fallback;
    }
  }
  return disposition.match(/filename="?([^";]+)"?/i)?.[1] || fallback;
}

async function requestBlob(path, { fallbackFilename = "download.xlsx", ...options } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...options,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return {
    blob: await response.blob(),
    filename: downloadFilename(response.headers?.get?.("content-disposition") || "", fallbackFilename),
  };
}

export const apiClient = {
  get: (path) => request(path, { cache: "no-store" }),
  getBlob: (path, options) => requestBlob(path, options),
  post: (path, body, options = {}) =>
    request(path, {
      method: "POST",
      body: JSON.stringify(body),
      ...options,
    }),
};
