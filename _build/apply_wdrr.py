#!/usr/bin/env python3
import sys, shutil

if len(sys.argv) > 1:
    B = sys.argv[1]
else:
    B = "/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6"
files = {
    "fq.h": B + "/include/net/fq.h",
    "fq_impl.h": B + "/include/net/fq_impl.h",
    "tx.c": B + "/net/mac80211/tx.c",
}
def sub(path, old, new, must=1):
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    n = s.count(old)
    if n != must:
        print("FAIL count=%d for %s" % (n, old[:60]))
        sys.exit(1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s.replace(old, new))
    print("OK %s (%d)" % (old[:50], n))

# backup
for k, p in files.items():
    shutil.copy2(p, p + ".wdrr.orig")

# 1) fq.h: add per-flow quantum field
sub(files["fq.h"],
    "\tint deficit;\n};",
    "\tint deficit;\n\tint quantum;\n};")

# 2) fq_impl.h: weighted DRR replenish
sub(files["fq_impl.h"],
    "\t\tflow->deficit += fq->quantum;",
    "\t\tflow->deficit += flow->quantum ? flow->quantum : fq->quantum;")

# 3) fq_impl.h: init per-flow quantum = 0
sub(files["fq_impl.h"],
    "\tINIT_LIST_HEAD(&flow->flowchain);\n\t__skb_queue_head_init(&flow->queue);\n}",
    "\tINIT_LIST_HEAD(&flow->flowchain);\n\t__skb_queue_head_init(&flow->queue);\n\tflow->quantum = 0;\n}")

WDRR_BLOCK = """/* Private WDRR scheduler: per-AC weight applied to the fq DRR quantum.
 * Sysfs: /sys/module/mac80211/parameters/fq_weight
 * 0 for an AC means use the global quantum (classic DRR).
 */
static int fq_weight[IEEE80211_NUM_ACS] = {1, 1, 1, 1};
module_param_array(fq_weight, int, NULL, 0644);
MODULE_PARM_DESC(fq_weight, "mac80211 WDRR: per-AC weight (x quantum); 0=global quantum");

static void ieee80211_wdrr_mark_loaded(void)
{
\tprintk_once(KERN_INFO "mac80211: private WDRR scheduler active "
\t\t    "(fq_weight=%d,%d,%d,%d)\\n",
\t\t    fq_weight[0], fq_weight[1], fq_weight[2], fq_weight[3]);
}
"""

# 4) tx.c: module params + marker right after fq_impl include
sub(files["tx.c"],
    "#include <net/fq_impl.h>\n",
    "#include <net/fq_impl.h>\n\n" + WDRR_BLOCK, 1)

# 5) tx.c: per-AC weight inside fq_tin_dequeue_func (single-line anchor)
sub(files["tx.c"],
    "\tcstats = &txqi->cstats;",
    "\tcstats = &txqi->cstats;\n\n\t/* Private WDRR: apply per-AC weight to this flow's DRR budget\n\t * on first dequeue; later sysfs updates affect newly created flows.\n\t */\n\tif (flow->quantum == 0) {\n\t\tint ac = txqi->txq.ac;\n\t\tint w = (ac >= 0 && ac < IEEE80211_NUM_ACS) ? fq_weight[ac] : 1;\n\n\t\tif (w <= 0)\n\t\t\tw = 1;\n\t\tflow->quantum = fq->quantum * w;\n\t\tieee80211_wdrr_mark_loaded();\n\t}", 1)

print("ALL_APPLIED")
