# Codex guidance for Docker infrastructure

This repository stores rebuild instructions, sanitized Compose definitions, backup tooling and restore documentation. It never stores live container data or credentials.

## Current scope

- `wg-easy/docker-compose.yml` is the authoritative source for the wg-easy Compose definition.
- Stream Monitor and its active Gotify service remain authoritative in `C:\Users\henk\stream-monitor`; do not duplicate their Compose source here.
- The Linux Docker host is normally `henk@10.50.50.1`.

## Safety boundary

- Never commit WireGuard configuration, private keys, wg-easy or Gotify databases, tokens, certificates, `.env` files, logs or backup archives.
- Container images are replaceable. Preserve image tags/digests and rebuild definitions rather than exporting images by default.
- Runtime backups are sensitive even when compressed. Keep them outside Git with restrictive permissions and copy them only to trusted storage.
- Inspect current live Compose and mount paths before installation or restore. Do not assume documentation proves the current runtime state.

## Working method

1. Make source changes in this repository and review the Git diff.
2. Validate Python, PowerShell, shell and Compose syntax.
3. Back up exact live targets before replacing installed scripts or units.
4. Install without enabling timers first, unless activation was explicitly requested.
5. Run and verify one manual backup before enabling a schedule.
6. Verify archive checksums and perform a documented restore test when practical.

Always distinguish repository preparation, installation, timer activation, backup creation and off-host copying in the final report.
