set -e
cd /root/merge
echo "=== file ==="
file sdcard.img | head -c 400; echo
LOOP=$(losetup -f --show -P sdcard.img)
echo "loop=$LOOP"
ls -la ${LOOP}* 2>/dev/null || true
echo "=== blkid ==="
blkid ${LOOP}* 2>&1 || true
echo "=== try mounts ==="
mkdir -p /root/merge/mnt
for p in 7 1 2 3 4 5 6; do
  if mount -o ro ${LOOP}p$p /root/merge/mnt 2>/dev/null; then
    echo "p$p MOUNT_OK type=$(findmnt -no FSTYPE /root/merge/mnt)";
    ls -la /root/merge/mnt | head -30;
    umount /root/merge/mnt;
  else
    echo "p$p mount failed";
  fi
done
losetup -d $LOOP
echo DONE