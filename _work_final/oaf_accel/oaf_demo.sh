#!/bin/sh
# OAF AI acceleration demo control
case "${1:-status}" in
  start)
    /root/oaf_start.sh
    echo "started"
    ;;
  stop)
    /root/oaf_accel.sh remove 2>/dev/null || true
    rmmod oaf 2>/dev/null || true
    echo "stopped"
    ;;
  status)
    echo "=== OAF ==="
    lsmod | grep '^oaf' || echo "not loaded"
    [ -r /proc/sys/fwx/appfilter_enable ] && echo "appfilter=$(cat /proc/sys/fwx/appfilter_enable) feature_init=$(cat /proc/sys/fwx/feature_init)"
    echo "=== ACCEL ==="
    nft list table ip oaf_accel 2>/dev/null || echo "no accel table"
    echo "=== DOUBAO CT (mark=1900) ==="
    grep -i 'mark=1900' /proc/net/nf_conntrack 2>/dev/null | head -5 || echo "none"
    echo "=== ACCEL COUNTER ==="
    nft -a list table ip oaf_accel 2>/dev/null | grep counter || true
    ;;
  watch)
    while true; do
      clear 2>/dev/null || true
      date
      echo "--- Doubao ct mark 1900 ---"
      grep -i 'mark=1900' /proc/net/nf_conntrack 2>/dev/null | wc -l
      echo "--- accel counter ---"
      nft -a list table ip oaf_accel 2>/dev/null | grep counter || true
      sleep 2
    done
    ;;
  *)
    echo "usage: $0 start|stop|status|watch"
    ;;
esac
