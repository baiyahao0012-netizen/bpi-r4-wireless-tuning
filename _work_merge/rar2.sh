export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /tmp/aptu.log 2>&1; echo "update rc=$?"
for pkg in p7zip-full libarchive-tools unar unrar-free; do
  echo "--- installing $pkg"
  apt-get install -y -qq $pkg > /tmp/i_$pkg.log 2>&1 && echo "  OK $pkg" || (echo "  FAIL $pkg"; tail -3 /tmp/i_$pkg.log)
done
for t in 7z 7za bsdtar unar unrar; do printf "%s -> " $t; command -v $t || echo MISSING; done
echo "=== try listing with whatever is available ==="
if command -v 7z >/dev/null; then 7z l /root/merge/incoming/backports-src.rar | head -60; fi
if command -v bsdtar >/dev/null; then echo "-- bsdtar --"; bsdtar -tf /root/merge/incoming/backports-src.rar 2>&1 | head -60; fi
if command -v unar >/dev/null; then echo "-- unar --"; unar -l /root/merge/incoming/backports-src.rar 2>&1 | head -60; fi
if command -v unrar >/dev/null; then echo "-- unrar --"; unrar l /root/merge/incoming/backports-src.rar 2>&1 | head -60; fi
echo DONE