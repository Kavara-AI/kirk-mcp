# Create the public GitHub repo — step-by-step (revised for UlyssesModel org)

## Context

- **Target repo**: `github.com/UlyssesModel/kirk-mcp`
- **Existing sibling public repos**: `kirk-runner`, `kirk-pipeline`, `tiberius-openshift`, `uhura`
- **Public/private split**: PUBLIC repo = MCP interface docs + configuration templates. PRIVATE (self-hosted GitLab at `git-kavara.ibis-allosaurus.ts.net`) = sealed engine + kirk-mcp server code.
- **Not GitLab**: even though you have paid GitLab cloud, GitHub is required because `github.com/mcp` (the GitHub MCP Registry) is GitHub-native. GitLab stays for private work.

## Prerequisites

1. You already have admin on `github.com/UlyssesModel` — no org creation needed.

2. **Kavara logo** (blocking directory cards, not repo creation)
   - 512×512 PNG, alpha channel
   - Save as `assets/kirk-logo-512.png` in the repo root
   - Can skip on first push; add before submitting to directories

## Step-by-step

```bash
# On your Mac (Terminal has TCC access to home directory)
mkdir -p ~/UlyssesModel-github
cd ~/UlyssesModel-github

# --- Get the seed files onto local disk (routing around TCC on ~/Documents) ---
# Route 1 (easiest): Finder — drag "github-kirk-mcp-public-repo-seed" from
#   ~/Documents/Claude/Projects/Project Cash in Hand/
#   to ~/UlyssesModel-github/, then rename to kirk-mcp
# Route 2 (Terminal-only if Finder is unavailable): use ssh-heredoc via desk-01
#   to reconstruct files — pattern from earlier in this session

mv github-kirk-mcp-public-repo-seed kirk-mcp
cd kirk-mcp

# Add the logo when ready (skip for now if not designed)
mkdir -p assets
# cp /path/to/kavara-logo-512.png assets/kirk-logo-512.png

# Initialize git
git init
git branch -M main
git add .
git commit -m "Initial public release — MCP interface documentation and configuration templates for kirk-mcp.kavara.ai"

# Create the repo on GitHub via CLI (fastest — install: brew install gh)
gh auth login  # if not already authenticated to UlyssesModel
gh repo create UlyssesModel/kirk-mcp \
  --public \
  --description "Kirk MCP — sealed density-operator engine for cross-section entropy scoring on financial signal data. Bit-exact vs QuantBot FY24 golden across 252 days. First 100 IU free." \
  --homepage "https://kirk-mcp.kavara.ai" \
  --source=. \
  --push

# OR manually via web:
# 1. Go to https://github.com/organizations/UlyssesModel/repositories/new
# 2. Name: kirk-mcp
# 3. Public
# 4. Description + homepage as above
# 5. Do NOT initialize with README/LICENSE/.gitignore (we have them)
# 6. Then: git remote add origin git@github.com:UlyssesModel/kirk-mcp.git && git push -u origin main

# Verify
open https://github.com/UlyssesModel/kirk-mcp
```

## After the repo exists

1. **Add repository topics** on GitHub (Settings > About > Topics):
   - `mcp`
   - `model-context-protocol`
   - `density-operator`
   - `machine-learning`
   - `financial-data`
   - `signal-processing`
   - `regime-detection`
   - `entropy`
   - `quantitative-finance`

2. **Set the repo description** (if not already):
   > Kirk MCP — sealed density-operator engine for cross-section entropy scoring on financial signal data. Bit-exact vs QuantBot FY24 golden across 252 days. First 100 IU free.

3. **Set the repo website** to `https://kirk-mcp.kavara.ai`

4. **Enable Discussions** (Settings > Features > Discussions) — for community Q&A, low overhead

5. **Add a repository social preview image** (Settings > Social preview) — 1280×640 PNG for OpenGraph. Not urgent but boosts click-through.

6. **Optional but valuable — pin the repo** on the UlyssesModel org profile so it shows up alongside kirk-runner/kirk-pipeline. Frontmost signal of what Kavara ships publicly.

## What to do next (unblocks directory submissions)

Once `github.com/UlyssesModel/kirk-mcp` is live:

1. **Submit to `github.com/mcp`** — likely auto-detected via repo topics + MCP-manifest-compatible content. Verify by searching https://github.com/mcp for "kirk" after 24 hours. If not auto-detected, submit via their form.

2. **Submit to `registry.modelcontextprotocol.io`** — clone https://github.com/modelcontextprotocol/registry, follow the publishing CLI to submit `server.json`.

3. **Submit to Anthropic Connectors Directory** — `https://claude.com/docs/connectors/building/submission`. Fill in the repo URL, endpoint, tool list. Anthropic explicitly reviews — read `https://claude.com/docs/connectors/building/review-criteria` first.

4. **Cursor and Antigravity** likely auto-inherit from the canonical MCP Registry. Verify after 48 hours.

## Do NOT include in the public repo

- Sealed engine binaries (`kirk_rs_edge.so`, `kirk_py`, `kirk_cascade` wheels) — Kavara IP
- Server-side code from private `kirk-mcp` repo (`entitlement.py`, `metering.py`, `stripe_billing.py`, `middleware.py`) — internal auth + billing logic
- Any `.env` files, credentials, secrets, or CF Access tokens
- Deployment configuration for kirk-mcp.kavara.ai
- LEAK-1 forbidden field names anywhere in text, config, or examples: `tau`, `learning_rate`, `cooling_rate`, `rho_hat_init_min`, `rho_hat_init_max`, `seed_base`, `enforce_purity`, `enforce_symmetry`, `potential_field_active`, `v_phi_loc`, `v_phi_scale`, `mask_col`, `mask_value`

If any leak lands: `git reset --hard`, force-push, rotate whatever was exposed.

## Discipline reminders

- Public repo advertises **C2 / C5 / C6** (MCP-accessible). C1 / C3 / C4 are named but tagged as Path B / wheel license only.
- Never conflate correctness (bit-exact FY24) and speed (823μs warm in-process) in the same sentence.
- Kirk is a scoring engine, not a trading strategy. No "how to trade" language.
- All copy pulls vocabulary from `[[kirk_canonical_capabilities_2026_07_20]]`.
