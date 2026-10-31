export const MAX_DELIVERY_ARTIFACT_BYTES = 10 * 1024 * 1024;

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function sha256Hex(data) {
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
}

export async function verifyDeliveryArtifact(parsedArtifactUrl, expectedHash, {
  fetchImpl = fetch,
  maxBytes = MAX_DELIVERY_ARTIFACT_BYTES,
} = {}) {
  let response;
  try {
    response = await fetchImpl(parsedArtifactUrl.href, {
      method: "GET",
      redirect: "error",
      headers: { Accept: "application/octet-stream" },
    });
  } catch {
    return "ARTIFACT_FETCH_FAILED";
  }
  if (!response.ok) return "ARTIFACT_FETCH_FAILED";
  const declaredLength = Number(response.headers.get("content-length") || "0");
  if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    try { await response.body?.cancel(); } catch {}
    return "ARTIFACT_TOO_LARGE";
  }
  if (!response.body) return "ARTIFACT_BODY_MISSING";
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        try { await reader.cancel(); } catch {}
        return "ARTIFACT_TOO_LARGE";
      }
      chunks.push(value);
    }
  } catch {
    try { await reader.cancel(); } catch {}
    return "ARTIFACT_FETCH_FAILED";
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const actualHash = await sha256Hex(bytes);
  return timingSafeEqual(actualHash, expectedHash) ? "VERIFIED" : "ARTIFACT_DIGEST_MISMATCH";
}
