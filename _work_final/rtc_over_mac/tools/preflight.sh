#!/bin/bash
# Preflight for the L2 AI experiments. Exits non-zero if the environment is not
# the one we intend to measure. Writes /tmp/preflight.json for the run record.
set -u
IFACE=${IFACE:-wlan1}
SSID_WANT=${SSID_WANT:-BPI-R4-5G}
AP=${AP:-192.168.240.1}
MAC_PI=${MAC_PI:-90:de:80:1c:6a:7a}
ok=1
fail() { echo "FAIL: $*"; ok=0; }

LINK=$(/sbin/iw dev "$IFACE" link 2>/dev/null || true)
case "$LINK" in
  *"Not connected"*|"") fail "$IFACE not connected";;
esac
SSID=$(printf '%s\n' "$LINK" | awk -F': ' '/SSID/{print $2; exit}')
FREQ=$(printf '%s\n' "$LINK" | awk '/freq:/{print $2; exit}')
SIG=$(printf '%s\n' "$LINK" | awk -F'signal: ' '/signal:/{print $2; exit}')
BITRATE=$(printf '%s\n' "$LINK" | head -n 1 | grep -o 'bitrate: [0-9.]*' | awk '{print $2}')
ADDR=$(ip -4 -br addr show "$IFACE" 2>/dev/null | awk '{print $3}')

[ "${SSID:-}" = "$SSID_WANT" ] || fail "ssid=${SSID:-none} want=$SSID_WANT"
# 5 GHz band check (4900-5895 MHz)
if [ -n "${FREQ:-}" ]; then
  awk -v f="$FREQ" 'BEGIN{exit !(f>=4900 && f<=5895)}' || fail "freq=$FREQ not 5GHz"
else
  fail "no freq"
fi
[ -n "${ADDR:-}" ] || fail "no IPv4 on $IFACE"

APSEES=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@"$AP" \
  "iw dev phy0.1-ap0 station dump 2>/dev/null | grep -c '$MAC_PI'" 2>/dev/null || echo 0)
[ "${APSEES:-0}" -ge 1 ] || fail "AP does not see $MAC_PI"

RESET=$(dmesg 2>/dev/null | grep -i 'mt7921' | tail -n 20 | grep -ci 'reset\|timeout' || true)
[ "${RESET:-0}" -eq 0 ] || echo "WARN: ${RESET} recent mt7921 reset/timeout lines in dmesg"

PWR=$(/sbin/iw dev "$IFACE" get power_save 2>/dev/null | awk '{print $3}')
[ "${PWR:-off}" = "off" ] || fail "power_save=$PWR"

JSON=$(printf '{"ts":"%s","iface":"%s","ssid":"%s","freq":%s,"signal":"%s","bitrate":"%s","addr":"%s","ap_sees_sta":%s,"power_save":"%s","ok":%s}' \
  "$(date -Is)" "$IFACE" "${SSID:-}" "${FREQ:-0}" "${SIG:-}" "${BITRATE:-}" "${ADDR:-}" "${APSEES:-0}" "${PWR:-}" \
  "$([ "$ok" -eq 1 ] && echo true || echo false)")
echo "$JSON" | tee /tmp/preflight.json
if [ "$ok" -ne 1 ]; then
  echo "PREFLIGHT_FAILED"
  exit 2
fi
echo "PREFLIGHT_OK"
