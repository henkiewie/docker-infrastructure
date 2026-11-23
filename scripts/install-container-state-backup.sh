#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer as root." >&2
    exit 1
fi

enable_timer=0
if [ "${1:-}" = "--enable" ]; then
    enable_timer=1
elif [ "$#" -gt 0 ]; then
    echo "Usage: $0 [--enable]" >&2
    exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname -- "$script_dir")
timestamp=$(date -u +%Y%m%d-%H%M%S)
backup_dir="/root/container-state-backup-installer-${timestamp}"

mkdir -p "$backup_dir"
for target in \
    /usr/local/sbin/backup-container-state.py \
    /etc/systemd/system/container-state-backup.service \
    /etc/systemd/system/container-state-backup.timer
do
    if [ -f "$target" ]; then
        cp -p "$target" "$backup_dir/"
    fi
done

install -d -m 0700 -o henk -g henk /home/henk/container-backups
install -m 0755 "$repo_dir/scripts/backup_container_state.py" \
    /usr/local/sbin/backup-container-state.py
install -m 0644 "$repo_dir/systemd/container-state-backup.service" \
    /etc/systemd/system/container-state-backup.service
install -m 0644 "$repo_dir/systemd/container-state-backup.timer" \
    /etc/systemd/system/container-state-backup.timer

systemctl daemon-reload

if [ "$enable_timer" -eq 1 ]; then
    systemctl enable --now container-state-backup.timer
    echo "Installed and enabled container-state-backup.timer."
else
    echo "Installed without enabling the timer."
    echo "Run a check first: sudo /usr/local/sbin/backup-container-state.py --check"
    echo "Then enable with: sudo systemctl enable --now container-state-backup.timer"
fi

echo "Previous installed files, when present, were copied to: $backup_dir"
