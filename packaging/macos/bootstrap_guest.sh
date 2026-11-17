#!/bin/bash
# Explicit disposable dedicated VM only. No host mounts, host sockets or autostart.
set -euo pipefail
test "$(uname -s)" = Linux
test "$(uname -m)" = aarch64
test "$#" = 1
case "$1" in *[!a-f0-9]*|'') exit 2;; esac
test "${#1}" = 40
test ! -e "$HOME/IGRIS"
test ! -L "$HOME/IGRIS"
# Refuse host filesystem mounts before installing anything in this guest.
if findmnt -rn -t 9p,virtiofs | read -r line; then
    echo 'BLOCKED: host filesystem sharing detected.' >&2
    exit 2
fi
# Signed distro packages in this dedicated guest; preserve pre-existing policy.
test ! -e /usr/sbin/policy-rc.d
printf '#!/bin/sh\nexit 101\n' | sudo tee /usr/sbin/policy-rc.d >/dev/null
sudo chmod 755 /usr/sbin/policy-rc.d
trap 'sudo rm -f /usr/sbin/policy-rc.d' EXIT
sudo apt-get update
sudo apt-get install -y --no-install-recommends git python3 python3-venv gcc libc6-dev ca-certificates docker.io
sudo systemctl disable docker.service docker.socket containerd.service
sudo rm -f /usr/sbin/policy-rc.d
trap - EXIT
sudo systemctl start docker.service
sudo usermod -aG docker "$(id -un)"
git clone --no-checkout https://github.com/Vishnu063/IGRIS.git "$HOME/IGRIS"
git -C "$HOME/IGRIS" fetch origin "$1"
git -C "$HOME/IGRIS" checkout --detach "$1"
# New group takes effect only in a fresh shell; model preparation is separate.
printf 'Guest source and packages prepared at %s. No assistant or model started.\n' "$1"
printf 'Next: run prepare_arm64_runtime.py --allow-downloads in a fresh guest shell.\n'
