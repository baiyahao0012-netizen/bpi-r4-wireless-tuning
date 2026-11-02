set -e
cd /root/merge
off() { echo $(( $1 * 512 )); }
for spec in "p1:34" "p2:8192" "p3:9216" "p4:13312" "p5:24576" "p6:90112" "p7:131072"; do
  p=${spec%%:*}; s=${spec##*:}; o=$(( s * 512 ));
  echo "===== $p offset=$o =====";
  dd if=sdcard.img bs=512 skip=$s count=8 2>/dev/null | xxd | head -8;
done
echo "===== ext superblock magics (0xEF53 at +0x438) =====";
for spec in "p1:34" "p2:8192" "p3:9216" "p4:13312" "p5:24576" "p6:90112" "p7:131072"; do
  p=${spec%%:*}; s=${spec##*:}; o=$(( s * 512 ));
  m=$(dd if=sdcard.img bs=1 skip=$(( o + 1080 )) count=2 2>/dev/null | xxd -p);
  echo "$p superblock_magic_at_1080=$m";
done
echo DONE