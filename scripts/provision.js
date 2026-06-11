#!/usr/bin/env node
/**
 * n8n Credential Provisioner
 * ─────────────────────────────────────────────────────────────────────────────
 * Runs as a one-shot Docker service after n8n-main starts.
 * Automatically creates PostgreSQL and Redis credentials in n8n.
 *
 * Idempotent — checks whether each credential already exists before
 * creating it, so it is safe to run on every `docker compose up`.
 *
 * Required env vars (inherited from .env via docker-compose):
 *   N8N_OWNER_EMAIL        — your n8n login e-mail
 *   N8N_OWNER_PASSWORD     — your n8n login password
 *   N8N_OWNER_FIRST_NAME   — (optional, default: Admin)
 *   N8N_OWNER_LAST_NAME    — (optional, default: User)
 *   DB_POSTGRESDB_HOST, DB_POSTGRESDB_PORT, DB_POSTGRESDB_DATABASE,
 *   DB_POSTGRESDB_USER, DB_POSTGRESDB_PASSWORD
 *
 * To add more credentials, append an entry to the CREDENTIALS array below.
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';

const N8N_URL        = 'http://n8n:5678';
const RETRY_MS       = 3_000;
const MAX_WAIT_MS    = 120_000;  // give n8n up to 2 minutes to boot

// ── Read environment ──────────────────────────────────────────────────────────
const {
  N8N_OWNER_EMAIL,
  N8N_OWNER_PASSWORD,
  N8N_OWNER_FIRST_NAME = 'Admin',
  N8N_OWNER_LAST_NAME  = 'User',
  DB_POSTGRESDB_HOST       = 'postgres',
  DB_POSTGRESDB_PORT       = '5432',
  DB_POSTGRESDB_DATABASE   = 'n8n',
  DB_POSTGRESDB_USER,
  DB_POSTGRESDB_PASSWORD,
} = process.env;

// ── Fail fast on missing required vars ───────────────────────────────────────
if (!N8N_OWNER_EMAIL || !N8N_OWNER_PASSWORD) {
  console.error(
    '[provision] ✗ N8N_OWNER_EMAIL and N8N_OWNER_PASSWORD must be set in .env\n' +
    '            These must match your n8n login credentials.',
  );
  process.exit(1);
}

// ── Credentials to provision ──────────────────────────────────────────────────
// Add more entries here to provision additional credentials automatically.
const CREDENTIALS = [
  // ── PostgreSQL ──────────────────────────────────────────────────────────────
  {
    name: 'PostgreSQL — n8n Stack',
    type: 'postgres',
    data: {
      host:                  DB_POSTGRESDB_HOST,
      port:                  parseInt(DB_POSTGRESDB_PORT, 10),
      database:              DB_POSTGRESDB_DATABASE,
      user:                  DB_POSTGRESDB_USER,
      password:              DB_POSTGRESDB_PASSWORD,
      ssl:                   'disable',        // internal Docker network — no TLS needed
      allowUnauthorizedCerts: false,
      sshTunnel:             false,
    },
  },

  // ── Redis ───────────────────────────────────────────────────────────────────
  {
    name: 'Redis — n8n Stack',
    type: 'redis',
    data: {
      host:     'redis',
      port:     6379,
      password: '',    // no password — access is restricted to the n8n-net bridge
      database: 0,
      ssl:      false,
    },
  },
];

// ── Utilities ─────────────────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log   = (...a) => console.log('[provision]', ...a);
const warn  = (...a) => console.warn('[provision] ⚠', ...a);

// Collect all Set-Cookie values from a fetch Response into one Cookie header.
function extractCookie(response) {
  // Node 20+ supports getSetCookie(); older runtimes fall back to get().
  const raw = typeof response.headers.getSetCookie === 'function'
    ? response.headers.getSetCookie()
    : [response.headers.get('set-cookie') ?? ''].filter(Boolean);

  return raw.map(c => c.split(';')[0]).join('; ');
}

// ── Step 1: Wait for n8n to pass its health check ────────────────────────────
async function waitForN8n() {
  log('Waiting for n8n...');
  const deadline = Date.now() + MAX_WAIT_MS;

  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${N8N_URL}/healthz`);
      if (res.ok) { log('n8n is ready.'); return; }
    } catch { /* still booting — keep waiting */ }
    await sleep(RETRY_MS);
  }

  throw new Error(`n8n did not become ready within ${MAX_WAIT_MS / 1000}s`);
}

// ── Step 2: Create owner account if this is a fresh instance ─────────────────
// The /api/v1/owner/setup endpoint returns 4xx when the account already exists.
// We treat any non-fatal error here as "already configured" and continue.
async function ensureOwner() {
  log('Ensuring owner account exists...');
  try {
    const res = await fetch(`${N8N_URL}/api/v1/owner/setup`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        email:     N8N_OWNER_EMAIL,
        firstName: N8N_OWNER_FIRST_NAME,
        lastName:  N8N_OWNER_LAST_NAME,
        password:  N8N_OWNER_PASSWORD,
      }),
    });
    if (res.ok) log('Owner account created (first run).');
    else        log(`Owner setup returned ${res.status} — account already configured.`);
  } catch (err) {
    warn('ensureOwner (non-fatal):', err.message);
  }
}

// ── Step 3: Login and return session cookie ───────────────────────────────────
async function login() {
  log(`Logging in as ${N8N_OWNER_EMAIL}...`);
  const res = await fetch(`${N8N_URL}/rest/login`, {
    method:  'POST',
    headers: {
      'Content-Type':     'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    // n8n 2.x uses 'emailOrLdapLoginId' as the email field name
    body: JSON.stringify({ emailOrLdapLoginId: N8N_OWNER_EMAIL, password: N8N_OWNER_PASSWORD }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(
      `Login failed (HTTP ${res.status}).\n` +
      `  Check that N8N_OWNER_EMAIL / N8N_OWNER_PASSWORD in .env\n` +
      `  match your n8n login credentials.\n` +
      `  Server said: ${body}`,
    );
  }

  const cookie = extractCookie(res);
  if (!cookie) throw new Error('Login succeeded but no session cookie was returned.');

  log('Login successful.');
  return cookie;
}

// ── Step 4: Fetch set of existing credential names ────────────────────────────
async function getExistingNames(cookie) {
  const res = await fetch(`${N8N_URL}/rest/credentials`, {
    headers: {
      'Cookie':           cookie,
      'X-Requested-With': 'XMLHttpRequest',
    },
  });

  if (!res.ok) throw new Error(`Could not list credentials (HTTP ${res.status})`);

  const json  = await res.json();
  const items = Array.isArray(json) ? json : (json.data ?? []);
  return new Set(items.map(c => c.name));
}

// ── Step 5: Create a single credential ───────────────────────────────────────
async function createCredential(cookie, cred) {
  const res = await fetch(`${N8N_URL}/rest/credentials`, {
    method:  'POST',
    headers: {
      'Content-Type':     'application/json',
      'Cookie':           cookie,
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify({ name: cred.name, type: cred.type, data: cred.data }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Failed to create "${cred.name}" (HTTP ${res.status}): ${body}`);
  }

  log(`✓ Created: "${cred.name}" (type: ${cred.type})`);
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  log('─'.repeat(60));
  log('n8n Credential Provisioner starting...');
  log('─'.repeat(60));

  await waitForN8n();
  await ensureOwner();

  const cookie   = await login();
  const existing = await getExistingNames(cookie);

  log(`Found ${existing.size} existing credential(s) in n8n.`);
  log(`Provisioning ${CREDENTIALS.length} credential(s)...`);

  let created = 0;
  let skipped = 0;

  for (const cred of CREDENTIALS) {
    if (existing.has(cred.name)) {
      log(`→ Skipped  "${cred.name}" — already exists.`);
      skipped++;
    } else {
      await createCredential(cookie, cred);
      created++;
    }
  }

  log('─'.repeat(60));
  log(`Done. Created: ${created}  Skipped: ${skipped}`);
  log('─'.repeat(60));
}

main().catch(err => {
  console.error('\n[provision] ✗ Fatal error:', err.message, '\n');
  process.exit(1);
});
