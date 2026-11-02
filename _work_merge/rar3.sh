cd /root/merge/incoming
rm -rf extracted && mkdir -p extracted
7z x -y -oextracted backports-src.rar > /tmp/rarx.log 2>&1 && echo EXTRACT_OK || (echo EXTRACT_FAIL; tail -10 /tmp/rarx.log)
echo "=== tree summary ==="
find extracted/backports-src -maxdepth 1 | head -20
echo "--- file count ---"
find extracted/backports-src -type f | wc -l
du -sh extracted/backports-src
echo "=== top-level files ==="
ls -la extracted/backports-src/
echo "=== backports tree top ==="
ls -la extracted/backports-src/backports-6.12.96/ | head -40
echo "=== any other dirs? ==="
find extracted/backports-src -maxdepth 2 -type d | head -40
echo DONE