echo "=== WSL memory ==="
free -m
echo "=== nproc ==="
nproc
echo "=== kernel build progress ==="
tail -3 /root/kernel_build.log 2>/dev/null || echo "no build log yet"
echo "--- out log ---"
cat /root/kernel_ftrace_out.log 2>/dev/null | tail -25
echo "=== load ==="
uptime
echo DONE