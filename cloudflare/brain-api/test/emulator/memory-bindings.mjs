/**
 * Deterministic in-memory test doubles for the Cloudflare bindings used by Brain.
 * This is a local contract emulator, not a replacement for Cloudflare's runtime.
 */
export class MemoryD1 {
  #tables = new Map();
  #serial = 0;

  prepare(sql) {
    const db = this;
    let bound = [];
    return {
      bind(...values) { bound = values; return this; },
      async run() {
        const q = sql.trim().replace(/\s+/g, " ").toLowerCase();
        if (q.startsWith("insert into")) {
          const table = q.match(/^insert into ([a-z0-9_]+)/)?.[1];
          if (!table) throw new Error("Unsupported INSERT");
          const rows = db.#tables.get(table) ?? [];
          rows.push({ values: [...bound], id: ++db.#serial });
          db.#tables.set(table, rows);
          return { success: true, meta: { changes: 1, last_row_id: db.#serial } };
        }
        if (q.startsWith("delete from")) {
          const table = q.match(/^delete from ([a-z0-9_]+)/)?.[1];
          if (!table) throw new Error("Unsupported DELETE");
          const old = db.#tables.get(table) ?? [];
          db.#tables.set(table, []);
          return { success: true, meta: { changes: old.length } };
        }
        throw new Error("MemoryD1 supports only INSERT and DELETE in this test adapter");
      },
      async first() {
        const q = sql.trim().replace(/\s+/g, " ").toLowerCase();
        const table = q.match(/\bfrom ([a-z0-9_]+)/)?.[1];
        if (!table || !q.startsWith("select")) throw new Error("Unsupported SELECT");
        const rows = db.#tables.get(table) ?? [];
        const row = rows[0];
        if (!row) return null;
        if (q.includes("count(")) return { count: rows.length };
        return { id: row.id, values: [...row.values] };
      },
      async all() {
        const q = sql.trim().replace(/\s+/g, " ").toLowerCase();
        const table = q.match(/\bfrom ([a-z0-9_]+)/)?.[1];
        if (!table || !q.startsWith("select")) throw new Error("Unsupported SELECT");
        return { success: true, results: (db.#tables.get(table) ?? []).map(r => ({ id: r.id, values: [...r.values] })) };
      }
    };
  }

  async batch(statements) {
    // Validate the complete batch before applying it; snapshot allows rollback on failure.
    const snapshot = new Map([...this.#tables].map(([k, v]) => [k, v.map(r => ({ ...r, values: [...r.values] }))]));
    const serial = this.#serial;
    try {
      const results = [];
      for (const statement of statements) results.push(await statement.run());
      return results;
    } catch (error) {
      this.#tables = snapshot;
      this.#serial = serial;
      throw error;
    }
  }

  async exec(sql) {
    const match = sql.trim().match(/^CREATE TABLE IF NOT EXISTS ([a-zA-Z0-9_]+)/i);
    if (!match) throw new Error("MemoryD1 exec supports CREATE TABLE IF NOT EXISTS only");
    if (!this.#tables.has(match[1].toLowerCase())) this.#tables.set(match[1].toLowerCase(), []);
    return { success: true };
  }
}

export class MemoryR2Bucket {
  #objects = new Map();

  async put(key, value, options = {}) {
    if (typeof key !== "string" || !key) throw new TypeError("R2 key must be a non-empty string");
    const bytes = value instanceof Uint8Array ? new Uint8Array(value) : new TextEncoder().encode(String(value));
    this.#objects.set(key, { bytes, httpMetadata: options.httpMetadata ?? {}, customMetadata: options.customMetadata ?? {} });
    return { key, size: bytes.byteLength, etag: `memory-${bytes.byteLength}-${this.#objects.size}` };
  }

  async get(key) {
    const item = this.#objects.get(key);
    if (!item) return null;
    const bytes = new Uint8Array(item.bytes);
    return {
      key, size: bytes.byteLength, httpMetadata: { ...item.httpMetadata },
      customMetadata: { ...item.customMetadata },
      async arrayBuffer() { return bytes.slice().buffer; },
      async text() { return new TextDecoder().decode(bytes); },
      async json() { return JSON.parse(new TextDecoder().decode(bytes)); },
    };
  }

  async head(key) {
    const item = this.#objects.get(key);
    return item ? { key, size: item.bytes.byteLength, httpMetadata: { ...item.httpMetadata }, customMetadata: { ...item.customMetadata } } : null;
  }

  async delete(keys) {
    for (const key of Array.isArray(keys) ? keys : [keys]) this.#objects.delete(key);
  }

  async list({ prefix = "", limit = 1000, cursor } = {}) {
    const keys = [...this.#objects.keys()].filter(k => k.startsWith(prefix)).sort();
    const start = cursor ? Math.max(0, Number(cursor)) : 0;
    const selected = keys.slice(start, start + limit);
    const next = start + selected.length;
    return { objects: selected.map(key => ({ key, size: this.#objects.get(key).bytes.byteLength })), truncated: next < keys.length, cursor: next < keys.length ? String(next) : undefined };
  }
}

export class MemoryQueue {
  #jobs = new Map();
  #next = 0;

  async send(body, options = {}) {
    const id = options.contentType === "json" ? undefined : undefined;
    const jobId = `job-${++this.#next}`;
    this.#jobs.set(jobId, { id: jobId, body: structuredClone(body), status: "queued", attempts: 0 });
    return { id: jobId };
  }

  async sendBatch(messages) {
    const result = [];
    for (const message of messages) result.push(await this.send(message.body, message));
    return result;
  }

  claim() {
    const job = [...this.#jobs.values()].find(item => item.status === "queued");
    if (!job) return null;
    job.status = "processing";
    job.attempts += 1;
    return structuredClone(job);
  }

  ack(id) {
    const job = this.#jobs.get(id);
    if (!job || job.status !== "processing") return false;
    job.status = "done";
    return true;
  }

  retry(id, maxAttempts = 3) {
    const job = this.#jobs.get(id);
    if (!job || job.status !== "processing") return false;
    job.status = job.attempts >= maxAttempts ? "dead" : "queued";
    return job.status === "queued";
  }

  get(id) {
    const job = this.#jobs.get(id);
    return job ? structuredClone(job) : null;
  }

  stats() {
    return [...this.#jobs.values()].reduce((out, job) => {
      out[job.status] = (out[job.status] ?? 0) + 1;
      return out;
    }, { queued: 0, processing: 0, done: 0, dead: 0 });
  }
}

export function createCloudflareBindings() {
  return {
    BRAIN_DB: new MemoryD1(),
    CINEMA_MEDIA: new MemoryR2Bucket(),
    BRAIN_QUEUE: new MemoryQueue(),
  };
}
