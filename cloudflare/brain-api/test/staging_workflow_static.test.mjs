import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workflow = readFileSync(
  ".github/workflows/brain-isolated-staging-gate.yml",
  "utf8",
);

const required = [
  "workflow_dispatch:",
  "github.event_name == 'workflow_dispatch'",
  "github.ref == 'refs/heads/main'",
  "environment: brain-staging",
  "STAGING_CLOUDFLARE_API_TOKEN",
  "STAGING_CLOUDFLARE_ACCOUNT_ID",
  "STAGING_D1_DATABASE_ID",
  "PAYTABS_SANDBOX_SERVER_KEY",
  "PAYTABS_SANDBOX_PROFILE_ID",
  'name = "brain-cloud-api-staging"',
  'database_name = "brain-commercial-staging"',
  'bucket_name = "brain-cinema-media-staging"',
  "STAGING_WORKER_URL/health",
  '"paytabs_transaction_performed": False',
  '"delivery_confirmed": False',
  '"revenue_realized": False',
];

for (const token of required) {
  assert.ok(workflow.includes(token), `staging workflow missing safety contract: ${token}`);
}

assert.ok(
  workflow.includes("production fallback is forbidden"),
  "missing fail-closed missing-secret behavior",
);
assert.ok(
  workflow.includes("STAGING_D1_DATABASE_ID must be a dedicated D1 database UUID"),
  "missing D1 ID format guard",
);
assert.ok(
  !/PAYTABS_MODE\s*[:=]\s*["']?live\b/i.test(workflow),
  "staging workflow must never force PayTabs live mode",
);
assert.ok(
  !/database_name\s*=\s*["']brain-commercial["']/i.test(workflow),
  "staging workflow must not bind the production-named database",
);
assert.ok(
  !/bucket_name\s*=\s*["']brain-cinema-media["']/i.test(workflow),
  "staging workflow must not bind the production-named R2 bucket",
);

console.log("STAGING_WORKFLOW_ISOLATION=PASS");
console.log("STAGING_SECRETS_FAIL_CLOSED=PASS");
console.log("STAGING_HEALTH_AND_EVIDENCE_CONTRACT=PASS");
console.log("STAGING_LIVE_PAYMENT_FORBIDDEN=PASS");
