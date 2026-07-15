import { API_BASE_URL } from "../config/api.js";

export function resolveSourceDownloadUrl(downloadUrl) {
  const value = String(downloadUrl || "");
  if (!value || /^[a-z][a-z\d+.-]*:/i.test(value)) return value;
  if (API_BASE_URL.startsWith("/")) return value;
  return new URL(value, API_BASE_URL).toString();
}

export async function downloadSourceFile(downloadUrl) {
  const url = resolveSourceDownloadUrl(downloadUrl);
  const response = await fetch(url);
  if (!response.ok) {
    let message = "";
    try {
      message = (await response.json()).error || "";
    } catch {
      message = await response.text();
    }
    throw new Error(message || `下载失败（HTTP ${response.status}）`);
  }
  const blobUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
}
