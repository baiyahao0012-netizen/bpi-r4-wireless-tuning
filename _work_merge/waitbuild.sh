for i in $(seq 1 55); do
  if grep -q "BUILD_RC=" /root/mac80211_build.log 2>/dev/null; then break; fi
  sleep 5
done
echo "=== build status ==="
grep "BUILD_RC=" /root/mac80211_build.log || echo "STILL RUNNING"
echo "=== errors ==="
grep -nE "error:|Error [0-9]|Patch failed" /root/mac80211_build.log | head -20
echo "=== tail ==="
tail -15 /root/mac80211_build.log
echo DONE