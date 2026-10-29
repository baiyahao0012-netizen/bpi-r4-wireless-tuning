#!/bin/sh
# Bai primary, DianGroup103 fallback.
IF=phy0.0-sta0
PRIMARY="Bai"
PKEY="12345678"
FALLBACK="DianGroup103"
FKEY="DianGroup2002"

log() { logger -t wifi-failover "$*"; echo "$(date '+%F %T') $*"; }

current_ssid() {
  iw dev "$IF" link 2>/dev/null | sed -n 's/.*SSID: //p' | head -1
}

ssid_visible() {
  iw dev "$IF" scan 2>/dev/null | grep -q "SSID: $1"
}

set_target() {
  ssid="$1"; key="$2"
  cur_cfg=$(uci -q get wireless.sta0.ssid)
  cur_key=$(uci -q get wireless.sta0.key)
  [ "$cur_cfg" = "$ssid" ] && [ "$cur_key" = "$key" ] && return 0
  log "switch to $ssid"
  uci set wireless.sta0.ssid="$ssid"
  uci set wireless.sta0.key="$key"
  uci set wireless.sta0.encryption='psk2'
  uci set wireless.sta0.disabled='0'
  uci commit wireless
  wifi reload
  sleep 15
}

# let network settle after boot
sleep 20

while true; do
  cur=$(current_ssid)
  if [ "$cur" = "$PRIMARY" ]; then
    sleep 30
    continue
  fi

  if [ -z "$cur" ]; then
    sleep 5
    cur=$(current_ssid)
  fi

  if ssid_visible "$PRIMARY"; then
    set_target "$PRIMARY" "$PKEY"
  else
    set_target "$FALLBACK" "$FKEY"
  fi
  sleep 30
done
