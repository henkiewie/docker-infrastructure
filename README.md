# Docker infrastructure and container-state backup

This private source repository preserves the rebuild definition for wg-easy and provides safe backup tooling for the sensitive runtime state used by wg-easy and Gotify.

## What is protected where

| Component | Rebuild source | Runtime state |
| --- | --- | --- |
| Stream Monitor | Private `stream-monitor` repository | Existing Stream Monitor database backup process |
| Gotify | Active Compose service in the `stream-monitor` repository | `/home/henk/gotify/data/gotify.db` |
| wg-easy | `wg-easy/docker-compose.yml` in this repository | `/home/mint/Templates/wg-easy/config/wg-easy.db` and `wg0.conf` |

Container images are not archived. They are replaceable from their registries; the Compose definitions preserve the required image references and runtime settings.

## Important security rule

The generated archives contain WireGuard private keys, VPN peer configuration and Gotify application data. They must never be committed to GitHub, attached to ordinary messages or stored in an untrusted cloud folder. Archive and checksum files are excluded by `.gitignore`.

## Installation without activation

Copy or clone this repository on the Docker host and run:

```sh
sudo ./scripts/install-container-state-backup.sh
```

The installer backs up any previously installed script/unit files, installs the new files and reloads systemd. It deliberately does not enable the timer.

Validate the live sources and databases without writing a backup:

```sh
sudo /usr/local/sbin/backup-container-state.py --check
```

Create and verify one manual backup:

```sh
sudo systemctl start container-state-backup.service
sudo systemctl status container-state-backup.service --no-pager
sudo journalctl -u container-state-backup.service -n 50 --no-pager
ls -l /home/henk/container-backups
sha256sum -c /home/henk/container-backups/container-state-*-utc.tar.gz.sha256
```

After the manual result has been inspected, enable the daily timer:

```sh
sudo systemctl enable --now container-state-backup.timer
systemctl list-timers container-state-backup.timer --no-pager
```

The timer runs daily at 02:30 UTC with a random delay of up to ten minutes. Backups are small, and automatic deletion is intentionally not included.

## Copy the latest backup off the Docker host

From the trusted Windows computer, run:

```powershell
Set-Location C:\Users\henk\docker-infrastructure
.\scripts\pull-latest-container-backup.ps1
```

This copies the newest archive and checksum into `C:\productie\backups\container-runtime` and verifies SHA-256. That destination must remain outside Git and should itself be included in a trusted offline or encrypted backup strategy.

## Restore outline

Restoration is deliberately manual because it replaces sensitive live state:

1. Verify the archive checksum before extraction.
2. Extract into a temporary directory, not directly over live paths.
3. Inspect `manifest.json` and verify the internal file hashes.
4. Stop only the affected container.
5. Back up its current live data again.
6. Restore the matching database/configuration files with their original ownership and restrictive permissions.
7. Start the affected container and verify its health and functionality.

Do not restore wg-easy or Gotify databases while their container is running. Do not replace Stream Monitor data using this archive; Stream Monitor has its own database workflow.
