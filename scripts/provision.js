#!/usr/bin/env node
/**
 * n8n Credential Provisioner — CLI-based (no login required)
 * ─────────────────────────────────────────────────────────────────────────────
 * Uses `n8n export:credentials` and `n8n import:credentials` directly.
 * Connects straight to PostgreSQL — n8n-main does NOT need to be running.
 *
 * Behaviour:
 *  - Adds missing credentials (PostgreSQL, Redis)
 *  - NEVER modifies or deletes credentials that already exist
 *  - Safe to run on every `docker compose up` (fully idempotent)
 *
 * Required env vars (from .env):
 *   N8N_ENCRYPTION_KEY       — the master encryption key
 *   DB_POSTGRESDB_HOST/PORT/DATABASE/USER/PASSWORD
 *
 * To add more credentials: append an entry to CREDENTIALS below.
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';

const { execSync }           = require('child_process');
const { randomUUID }         = require('crypto');
const fs                     = require('fs');
const path                   = require('path');
const os                     = require('os');

// ── Utilities ─────────────────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log   = (...a) => console.log('[provision]', ...a);
const line  = ()     => console.log('[provision]', '─'.repeat(55));

// ── Credential definitions ────────────────────────────────────────────────────
// Data fields are PLAINTEXT — n8n encrypts them on import using N8N_ENCRYPTION_KEY.
// Only modify 'name', 'type', and 'data'. Do not set 'id'.
const {
  DB_POSTGRESDB_HOST     = 'postgres',
  DB_POSTGRESDB_PORT     = '5432',
  DB_POSTGRESDB_DATABASE = 'n8n',
  DB_POSTGRESDB_USER,
  DB_POSTGRESDB_PASSWORD,
  WAHA_API_URL           = 'http://waha:3000',
  WAHA_API_KEY           = 'admin',
  MSSQL_HOST             = 'host.docker.internal',
  MSSQL_PORT             = '1433',
  MSSQL_DATABASE         = 'master',
  MSSQL_USER,
  MSSQL_PASSWORD,
  MSSQL_DOMAIN,
} = process.env;

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
      ssl:                   'disable',       // internal Docker network — no TLS
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
      password: '',     // no password — access restricted to n8n-net bridge
      database: 0,
      ssl:      false,
    },
  },

  // ── WAHA API ────────────────────────────────────────────────────────────────
  {
    name: 'WAHA API — n8n Stack',
    type: 'wahaApi',
    data: {
      apiUrl: WAHA_API_URL,
      apiKey: WAHA_API_KEY,
    },
  },

  // ── Ollama ──────────────────────────────────────────────────────────────────
  {
    name: 'Ollama — n8n Stack',
    type: 'ollamaApi',
    data: {
      baseUrl: 'http://host.docker.internal:11434',
    },
  },

  // ── Microsoft SQL Server ──────────────────────────────────────────────────
  {
    name: 'Microsoft SQL Server — n8n Stack',
    type: 'microsoftSql',
    data: {
      server:                MSSQL_HOST,
      port:                  parseInt(MSSQL_PORT, 10) || 1433,
      database:              MSSQL_DATABASE || 'master',
      user:                  MSSQL_USER || '',
      password:              MSSQL_PASSWORD || '',
      domain:                MSSQL_DOMAIN || '',
      tls:                   false,
      allowUnauthorizedCerts: true,
    },
  },
];

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  line();
  log('n8n Credential Provisioner starting (CLI mode)');
  log('Will ONLY add missing credentials — existing ones are never touched.');
  line();

  const tmpDir      = os.tmpdir();
  const exportFile  = path.join(tmpDir, 'n8n-existing-creds.json');
  const importFile  = path.join(tmpDir, 'n8n-import-creds.json');

  // ── Step 1: Wait for the database + n8n migrations to be ready ─────────────
  // We run `n8n export:credentials` in a retry loop.
  // It succeeds once the DB is up and the credentials_entity table exists
  // (i.e., after n8n has run its schema migrations on first start).
  log('Waiting for n8n database to be ready...');
  const deadline = Date.now() + 600_000;   // 10-minute timeout
  let existing   = [];

  while (true) {
    try {
      execSync(`n8n export:credentials --all --output="${exportFile}"`, {
        stdio:   'pipe',
        timeout: 180_000, // 3-minute timeout to account for slow host systems
        env:     process.env,
      });

      const raw = fs.existsSync(exportFile)
        ? fs.readFileSync(exportFile, 'utf8').trim()
        : '';
      existing = raw ? JSON.parse(raw) : [];
      break;   // success — proceed
    } catch (err) {
      if (Date.now() >= deadline) {
        throw new Error('Database never became ready within 10 minutes. ' +
                        'Check postgres container logs.');
      }
      log(`Database not ready yet — retrying in 3s... Error: ${err.message}`);
      if (err.stdout) log('stdout:', err.stdout.toString());
      if (err.stderr) log('stderr:', err.stderr.toString());
      await sleep(3_000);
    }
  }

  // ── Step 1.5: Install WAHA Community Node ─────────────────────────────────
  log('Checking/Installing WAHA Community Node...');
  const nodesDir = '/home/node/.n8n/nodes';
  const pkgJsonPath = path.join(nodesDir, 'package.json');
  let isInstalled = false;
  try {
    if (fs.existsSync(pkgJsonPath)) {
      const pkg = JSON.parse(fs.readFileSync(pkgJsonPath, 'utf8'));
      if (pkg.dependencies && pkg.dependencies['@devlikeapro/n8n-nodes-waha']) {
        isInstalled = true;
      }
    }
  } catch (e) {
    log('Error checking package.json:', e.message);
  }

  if (isInstalled) {
    log('WAHA Community Node is already installed. Skipping npm install.');
  } else {
    try {
      fs.mkdirSync(nodesDir, { recursive: true });
      execSync(`npm install --prefix "${nodesDir}" @devlikeapro/n8n-nodes-waha --omit=dev --no-audit --no-fund`, {
        stdio:   'inherit',
        timeout: 180_000,
        env:     process.env,
      });
      log('WAHA Community Node checked/installed successfully.');
    } catch (err) {
      log('Warning: Failed to auto-install WAHA community node:', err.message);
    }
  }

  // ── Step 2: Determine what to create ─────────────────────────────────────
  const existingNames = new Set(existing.map(c => c.name));

  if (existingNames.size > 0) {
    log(`Found ${existingNames.size} existing credential(s):`);
    for (const name of existingNames) log(`  • ${name}`);
  } else {
    log('No existing credentials found.');
  }

  const toCreate = CREDENTIALS.filter(c => !existingNames.has(c.name) || c.type === 'microsoftSql');

  if (toCreate.length === 0) {
    log('All target credentials already exist — nothing to do.');
    line();
    return;
  }

  log(`Need to create/update ${toCreate.length} credential(s):`);
  for (const c of toCreate) {
    const action = existingNames.has(c.name) ? 'update' : 'create';
    log(`  + ${c.name}  (type: ${c.type}, action: ${action})`);
  }

  // ── Step 3: Write import file and run n8n import:credentials ─────────────
  // n8n's credentials_entity.id is NOT NULL — each credential must carry a UUID.
  const toCreateWithIds = toCreate.map(c => {
    const matched = existing.find(e => e.name === c.name);
    return {
      id: matched ? matched.id : randomUUID(),
      ...c
    };
  });
  fs.writeFileSync(importFile, JSON.stringify(toCreateWithIds, null, 2), 'utf8');

  execSync(`n8n import:credentials --input="${importFile}"`, {
    stdio:   'inherit',   // show n8n's own output
    timeout: 30_000,
    env:     process.env,
  });

  line();
  log(`Done. Processed: ${toCreate.length}`);
  line();
}

main().catch(err => {
  console.error('\n[provision] ✗ Fatal error:', err.message, '\n');
  process.exit(1);
});
