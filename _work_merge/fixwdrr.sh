SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
rm -rf /root/merge/wdrr-gen && mkdir -p /root/merge/wdrr-gen/a /root/merge/wdrr-gen/b
cd /root/merge/wdrr-gen
tar -xf $SDK/dl/backports-6.12.6.tar.xz -C a --strip-components=1
tar -xf $SDK/dl/backports-6.12.6.tar.xz -C b --strip-components=1
echo "=== apply edits to b ==="
cp "/mnt/d/Desktop/AI 辅助对话/_build/apply_wdrr.py" /root/merge/wdrr-gen/apply_wdrr.py
python3 apply_wdrr.py /root/merge/wdrr-gen/b
echo "=== remove backups before diff ==="
find b -name "*.wdrr.orig" -delete
find a -name "*.wdrr.orig" -delete
echo "=== verify edits ==="
grep -n "quantum" b/include/net/fq.h b/include/net/fq_impl.h | head
grep -n "fq_weight" b/net/mac80211/tx.c | head
echo "=== generate patch ==="
diff -ruN a b > 360-wdrr-private-scheduler.patch; echo "diff rc=$?"
wc -l 360-wdrr-private-scheduler.patch
echo "=== dry-run check on pristine ==="
cd /root/merge/pristine
patch -p1 --dry-run < /root/merge/wdrr-gen/360-wdrr-private-scheduler.patch 2>&1 | head -20
echo "=== install into SDK patches ==="
cp /root/merge/wdrr-gen/360-wdrr-private-scheduler.patch $SDK/package/kernel/mac80211/patches/subsys/360-wdrr-private-scheduler.patch && echo INSTALLED
cp /root/merge/wdrr-gen/360-wdrr-private-scheduler.patch "/mnt/d/Desktop/AI 辅助对话/_work_merge/360-wdrr-private-scheduler.patch" && echo SAVED_TO_WIN
echo DONE