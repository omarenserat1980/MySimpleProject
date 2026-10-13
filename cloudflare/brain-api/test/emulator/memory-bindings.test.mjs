import test from "node:test";
import assert from "node:assert/strict";
import { createCloudflareBindings } from "./memory-bindings.mjs";

test("D1 adapter supports isolated inserts, reads, counts, and batch rollback", async () => {
  const { BRAIN_DB: db } = createCloudflareBindings();
  await db.exec("CREATE TABLE IF NOT EXISTS events (id INTEGER, name TEXT)");
  await db.prepare("INSERT INTO events (name) VALUES (?)").bind("payment-pending").run();
  assert.deepEqual(await db.prepare("SELECT * FROM events").first(), { id: 1, values: ["payment-pending"] });
  assert.deepEqual(await db.prepare("SELECT COUNT(*) AS count FROM events").first(), { count: 1 });
  await assert.rejects(db.batch([
    db.prepare("INSERT INTO events (name) VALUES (?)").bind("temporary"),
    db.prepare("UPDATE events SET name = ?").bind("unsupported"),
  ]), /Unsupported/);
  assert.equal((await db.prepare("SELECT COUNT(*) AS count FROM events").first()).count, 1);
});

test("R2 adapter stores bytes, metadata, prefix lists, and deletes", async () => {
  const { CINEMA_MEDIA: bucket } = createCloudflareBindings();
  await bucket.put("films/a.json", JSON.stringify({ ready: true }), {
    httpMetadata: { contentType: "application/json" }, customMetadata: { source: "test" },
  });
  await bucket.put("other.txt", "ignored");
  const item = await bucket.get("films/a.json");
  assert.deepEqual(await item.json(), { ready: true });
  assert.equal((await bucket.head("films/a.json")).customMetadata.source, "test");
  assert.deepEqual((await bucket.list({ prefix: "films/" })).objects.map(x => x.key), ["films/a.json"]);
  await bucket.delete("films/a.json");
  assert.equal(await bucket.get("films/a.json"), null);
});

test("queue claims jobs once, retries, acknowledges, and dead-letters after limit", async () => {
  const { BRAIN_QUEUE: queue } = createCloudflareBindings();
  const { id } = await queue.send({ type: "render", filmId: "film-1" });
  const first = queue.claim();
  assert.equal(first.id, id);
  assert.equal(first.attempts, 1);
  assert.equal(queue.claim(), null);
  assert.equal(queue.retry(id, 2), true);
  assert.equal(queue.claim().attempts, 2);
  assert.equal(queue.retry(id, 2), false);
  assert.equal(queue.get(id).status, "dead");
  const { id: secondId } = await queue.send({ type: "deliver" });
  queue.claim();
  assert.equal(queue.ack(secondId), true);
  assert.equal(queue.get(secondId).status, "done");
  assert.deepEqual(queue.stats(), { queued: 0, processing: 0, done: 1, dead: 1 });
});
