#!/bin/sh
# OAF AppID -> DSCP/AC acceleration
# usage:
#   oaf_accel.sh install [app_id] [dscp]
#   oaf_accel.sh remove
#   oaf_accel.sh status [app_id]
#   oaf_accel.sh verify [app_id]
# default: app_id=1900 (Doubao), dscp=ef
set -e
CMD="${1:-status}"
APPID="${2:-1900}"
DSCP="${3:-ef}"
APPID_HEX=$(printf '0x%04x' "$APPID")

install_rules() {
    nft delete table ip oaf_accel 2>/dev/null || true
    nft delete table ip6 oaf_accel 2>/dev/null || true
    nft -f - <<EOF
add table ip oaf_accel
add chain ip oaf_accel post { type filter hook postrouting priority mangle; }
add rule ip oaf_accel post ct mark & 0x0000ffff == $APPID_HEX counter ip dscp set $DSCP
add table ip6 oaf_accel
add chain ip6 oaf_accel post { type filter hook postrouting priority mangle; }
add rule ip6 oaf_accel post ct mark & 0x0000ffff == $APPID_HEX counter ip6 dscp set $DSCP
EOF
    echo "installed: app_id=$APPID (0x$(printf '%x' "$APPID")) dscp=$DSCP"
}

remove_rules() {
    nft delete table ip oaf_accel 2>/dev/null || true
    nft delete table ip6 oaf_accel 2>/dev/null || true
    echo "removed"
}

show_status() {
    echo "=== ip ==="
    nft list table ip oaf_accel 2>/dev/null || echo "(not installed)"
    echo "=== ip6 ==="
    nft list table ip6 oaf_accel 2>/dev/null || echo "(not installed)"
    echo "=== OAF active rows (app_id=$APPID) ==="
    if [ -r /proc/net/af_active_app ]; then
        awk -v id="$APPID" 'NR>1 && $1==id {c++} END{printf "rows=%d\n", c+0}' /proc/net/af_active_app
    else
        echo "(no /proc/net/af_active_app; OAF not loaded?)"
    fi
}

verify_rules() {
    show_status
    echo "=== nft counters ==="
    nft -s list table ip oaf_accel 2>/dev/null | grep -E 'counter|dscp' || true
    echo "=== conntrack marks (low16 == app_id) ==="
    if [ -r /proc/net/nf_conntrack ]; then
        grep -i "mark=0x$(printf '%x' "$APPID")" /proc/net/nf_conntrack | head -5 || echo "(none yet; generate Doubao traffic)"
    else
        echo "(no /proc/net/nf_conntrack)"
    fi
}

case "$CMD" in
    install) install_rules ;;
    remove) remove_rules ;;
    status) show_status ;;
    verify) verify_rules ;;
    *) echo "usage: $0 install|remove|status|verify [app_id] [dscp]"; exit 1 ;;
esac
