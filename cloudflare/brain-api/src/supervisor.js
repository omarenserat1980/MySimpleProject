export async function supervisorTick(env) {
  if (!env.BRAIN_DB) return { ok: false, state: "D1_NOT_CONFIGURED" };

  const stale = await env.BRAIN_DB.prepare(
    "SELECT job_id, order_id, state, attempt, updated_at FROM service_jobs WHERE state = 'RUNNING' AND updated_at < datetime('now', '-30 minutes') AND attempt < 3 LIMIT 20"
  ).all();

  let retried = 0;
  for (const job of stale.results || []) {
    const result = await env.BRAIN_DB.prepare(
      "UPDATE service_jobs SET state = 'RETRYING', updated_at = CURRENT_TIMESTAMP WHERE job_id = ? AND state = 'RUNNING' AND attempt < 3"
    ).bind(job.job_id).run();
    if (result.success) retried++;
  }

  const pending = await env.BRAIN_DB.prepare(
    "SELECT COUNT(*) AS count FROM service_jobs WHERE state IN ('PENDING','RETRYING') AND attempt < 3"
  ).first();

  return {
    ok: true,
    stale_detected: stale.results?.length || 0,
    retried,
    pending: Number(pending?.count || 0)
  };
}
