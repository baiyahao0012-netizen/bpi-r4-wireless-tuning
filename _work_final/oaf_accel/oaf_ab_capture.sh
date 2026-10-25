#!/bin/sh
# Capture A/B evidence on the OAF AP.
# usage: oaf_ab_capture.sh <label> <seconds> [iface] [outdir]
# example: sh oaf_ab_capture.sh A 180 br-oaf /tmp/oaf_ab_A
set -e
LABEL="${1:-A}"
DUR="${2:-180}"
IFACE="${3:-br-oaf}"
OUT="${4:-/tmp/oaf_ab_$LABEL}"
mkdir -p "$OUT"
if ! ip link show "$IFACE" >/dev/null 2>&1; then
    if ip link show br-lan >/dev/null 2>&1; then
        IFACE=br-lan
    else
        echo "no usable bridge interface"; exit 1
    fi
fi
echo "label=$LABEL iface=$IFACE duration=$DUR out=$OUT"
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/start_utc.txt"
nft list ruleset > "$OUT/nft_before.txt" 2>&1 || true
cat /proc/net/af_active_app > "$OUT/app_before.txt" 2>&1 || true
ip -s link show "$IFACE" > "$OUT/link_before.txt" 2>&1 || true

if command -v tcpdump >/dev/null 2>&1; then
    tcpdump -i "$IFACE" -nn -s0 -w "$OUT/capture.pcap" 2>"$OUT/tcpdump.err" &
    TCPPID=$!
else
    TCPPID=""
    echo "tcpdump not found; no pcap" > "$OUT/tcpdump.err"
fi

i=0
: > "$OUT/app_samples.txt"
while [ "$i" -lt "$DUR" ]; do
    now=$(date +%s)
    echo "--- t=$now ---" >> "$OUT/app_samples.txt"
    cat /proc/net/af_active_app >> "$OUT/app_samples.txt" 2>/dev/null || true
    sleep 1
    i=$((i+1))
done

if [ -n "$TCPPID" ]; then
    kill "$TCPPID" 2>/dev/null || true
    wait "$TCPPID" 2>/dev/null || true
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/end_utc.txt"
nft list ruleset > "$OUT/nft_after.txt" 2>&1 || true
cat /proc/net/af_active_app > "$OUT/app_after.txt" 2>&1 || true
ip -s link show "$IFACE" > "$OUT/link_after.txt" 2>&1 || true

{
    echo "OAF A/B capture"
    echo "label=$LABEL"
    echo "iface=$IFACE"
    echo "duration=$DUR"
    echo "start=$(cat "$OUT/start_utc.txt")"
    echo "end=$(cat "$OUT/end_utc.txt")"
    echo "app_rows_1900=$(awk 'NR>1 && $1==1900 {c++} END{print c+0}' "$OUT/app_after.txt" 2>/dev/null || echo 0)"
    echo "files: capture.pcap app_samples.txt nft_before/after.txt"
} > "$OUT/summary.txt"
echo "done: $OUT/summary.txt"
