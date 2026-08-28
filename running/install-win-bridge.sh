#!/usr/bin/env bash
# One-time install of the Windows bridge. Run once with sudo; idempotent.
#
#   sudo ~/eng/running/install-win-bridge.sh
#
# Re-run it after editing win-bridge — the installed copy under /usr/local/sbin
# is what sudo actually executes, not the one in this repo.
#
# Installs the mount script as root-owned, then grants <your-user> a NOPASSWD rule for
# that one script and nothing else. Every other sudo command keeps asking for the
# password, which is what keeps `sudo mount -t drvfs C: /mnt/c` out of reach.

set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run this with sudo" >&2; exit 1; }

SRC_DIR=$(cd "$(dirname "$0")" && pwd)
SUDO_USER_NAME=${SUDO_USER:-<your-user>}

install -o root -g root -m 0755 "$SRC_DIR/win-bridge" /usr/local/sbin/win-bridge

# Validate the sudoers snippet before putting it in place — a broken file in
# /etc/sudoers.d locks sudo out entirely.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
printf '%s ALL=(root) NOPASSWD: /usr/local/sbin/win-bridge\n' "$SUDO_USER_NAME" >"$tmp"
visudo -cf "$tmp"
install -o root -g root -m 0440 "$tmp" /etc/sudoers.d/win-bridge

visudo -c
echo "installed: sudo win-bridge mount | status | umount"
