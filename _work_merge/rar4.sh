cd /root/merge/incoming
echo "=== how many non-empty from 7z ==="
find extracted -type f -size +0 | wc -l; find extracted -type f -size 0 | wc -l
echo "=== try bsdtar ==="
rm -rf t_bsd && mkdir t_bsd && bsdtar -xf backports-src.rar -C t_bsd 2>&1 | head -5; ls -la t_bsd/backports-src/ 2>/dev/null | head -12
echo "=== try unar ==="
rm -rf t_unar && mkdir t_unar && unar -q -o t_unar backports-src.rar 2>&1 | tail -5; ls -la t_unar/backports-src/ 2>/dev/null | head -12
echo "=== try unrar-free ==="
rm -rf t_uf && mkdir t_uf && (cd t_uf && unrar-free -x ../backports-src.rar 2>&1 | tail -5); ls -la t_uf/backports-src/ 2>/dev/null | head -12
echo DONE