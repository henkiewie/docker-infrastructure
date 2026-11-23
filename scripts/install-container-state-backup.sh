#!/bin/sh
set -eu

enable_schedule=0
if [ "${1:-}" = "--enable" ]; then
    enable_schedule=1
elif [ "$#" -gt 0 ]; then
    echo "Usage: $0 [--enable]" >&2
    exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname -- "$script_dir")
install_dir="$HOME/.local/bin"
state_dir="$HOME/.local/state/container-state-backup"
backup_dir="$HOME/container-backups"
installed_script="$install_dir/backup-container-state.py"
timestamp=$(date -u +%Y%m%d-%H%M%S)
cron_backup="$state_dir/crontab-before-${timestamp}.txt"

install -d -m 0700 "$install_dir" "$state_dir" "$backup_dir"
if [ -f "$installed_script" ]; then
    cp -p "$installed_script" "$state_dir/backup-container-state-${timestamp}.py"
fi
install -m 0755 "$repo_dir/scripts/backup_container_state.py" "$installed_script"

current_cron=$(mktemp)
updated_cron=$(mktemp)
trap 'rm -f "$current_cron" "$updated_cron"' EXIT HUP INT TERM
crontab -l >"$current_cron" 2>/dev/null || :
cp "$current_cron" "$cron_backup"

if [ "$enable_schedule" -eq 1 ]; then
    awk '
        $0 == "# BEGIN container-state-backup" { skip = 1; next }
        $0 == "# END container-state-backup" { skip = 0; next }
        !skip { print }
    ' "$current_cron" >"$updated_cron"
    {
        echo "# BEGIN container-state-backup"
        echo "17 2 * * * /usr/bin/python3 $installed_script >> $backup_dir/backup.log 2>&1"
        echo "# END container-state-backup"
    } >>"$updated_cron"
    crontab "$updated_cron"
    echo "Installed and enabled the daily 02:17 server-time cron schedule."
else
    echo "Installed without changing the current crontab."
    echo "Run a check: $installed_script --check"
    echo "Create one manual backup: $installed_script"
    echo "Enable later with: $0 --enable"
fi

echo "Previous script/crontab state is under: $state_dir"
