echo "=== disk ==="
df -h / /root /tmp | head -10
echo "=== wsl mem ==="
free -h | head -3
echo "=== nproc ==="
nproc
echo "=== existing /root/sdk? ==="
ls -la /root/ 2>/dev/null | head -20
echo "=== /root/merge ==="
du -sh /root/merge/* 2>/dev/null | head -20
echo "=== net check ==="
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 15 https://downloads.openwrt.org/ 2>&1 || echo NET_FAIL
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 15 https://github.com/ 2>&1 || echo NET_FAIL2
echo DONE