import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { verifyDeliveryArtifact } from "../src/artifact-verifier.mjs";

const url = new URL("https://artifacts.example.test/product.bin");
const bytes = new TextEncoder().encode("electronic-brain-artifact");
const digest = createHash("sha256").update(bytes).digest("hex");
const response = (body, headers = {}) => new Response(body, { status: 200, headers });

let receivedOptions;
assert.equal(await verifyDeliveryArtifact(url, digest, {
  fetchImpl: async (_url, options) => { receivedOptions = options; return response(bytes); },
}), "VERIFIED");
assert.equal(receivedOptions.method, "GET");
assert.equal(receivedOptions.redirect, "error");

assert.equal(await verifyDeliveryArtifact(url, "0".repeat(64), {
  fetchImpl: async () => response(bytes),
}), "ARTIFACT_DIGEST_MISMATCH");

assert.equal(await verifyDeliveryArtifact(url, digest, {
  fetchImpl: async () => response(null, { "content-length": "9" }),
}), "ARTIFACT_BODY_MISSING");

assert.equal(await verifyDeliveryArtifact(url, digest, {
  maxBytes: 8,
  fetchImpl: async () => response(bytes),
}), "ARTIFACT_TOO_LARGE");

let oversizedStreamRead = false;
assert.equal(await verifyDeliveryArtifact(url, digest, {
  maxBytes: 8,
  fetchImpl: async () => new Response(new ReadableStream({
    pull(controller) {
      oversizedStreamRead = true;
      controller.enqueue(bytes);
    },
  }), { status: 200, headers: { "content-length": String(bytes.byteLength) } }),
}), "ARTIFACT_TOO_LARGE");
assert.equal(oversizedStreamRead, false, "declared oversized body should be rejected before reading");

assert.equal(await verifyDeliveryArtifact(url, digest, {
  fetchImpl: async () => new Response("unavailable", { status: 503 }),
}), "ARTIFACT_FETCH_FAILED");

assert.equal(await verifyDeliveryArtifact(url, digest, {
  fetchImpl: async () => { throw new Error("network failure"); },
}), "ARTIFACT_FETCH_FAILED");

const brokenStream = new ReadableStream({
  start(controller) {
    controller.enqueue(new Uint8Array([1, 2, 3]));
    controller.error(new Error("stream interrupted"));
  },
});
assert.equal(await verifyDeliveryArtifact(url, digest, {
  fetchImpl: async () => new Response(brokenStream, { status: 200 }),
}), "ARTIFACT_FETCH_FAILED");

console.log("DELIVERY_ARTIFACT_VERIFIER_RUNTIME_TEST=PASS");
