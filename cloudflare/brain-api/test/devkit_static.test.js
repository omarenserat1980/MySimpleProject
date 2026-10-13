import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import test from "node:test";

const devkit = readFileSync("scripts/brain-cloudflare-devkit.sh", "utf8");
const mode = readFileSync("scripts/brain-cloudflare-mode.sh", "utf8");
const promptPath = "../../docs/prompts/CHATGPT_CLOUDFLARE_EMULATOR_PROMPTS_AR.md";

test("devkit offers emulator-safe developer commands", () => {
  for (const command of ["status", "doctor", "test", "dev", "prompts", "deploy"]) {
    assert.ok(devkit.includes(command), `missing command: ${command}`);
  }
  assert.match(devkit, /BRAIN_CLOUDFLARE_MODE:-emulator/);
});

test("live deploy remains explicit opt-in only", () => {
  assert.match(mode, /BRAIN_CLOUDFLARE_MODE:-emulator/);
  assert.match(mode, /BRAIN_CLOUDFLARE_REAL/);
  assert.match(mode, /CLOUDFLARE_API_TOKEN/);
  assert.match(mode, /CLOUDFLARE_ACCOUNT_ID/);
  assert.match(devkit, /brain-cloudflare-mode\.sh deploy/);
});

test("Arabic ChatGPT prompt pack exists and includes safe review guidance", () => {
  assert.ok(existsSync(promptPath), `missing prompt pack: ${promptPath}`);
  const prompts = readFileSync(promptPath, "utf8");
  assert.match(prompts, /لا تنفذ النشر الحقيقي/);
  assert.match(prompts, /اختبارات/);
  assert.match(prompts, /الأسرار/);
});
