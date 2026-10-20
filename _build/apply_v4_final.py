#!/usr/bin/env python3
# apply_v4_final.py — deterministic BA window push: re-replay STA_REC_BA TLV at write time.
# Changes:
#   mt7996.h : add agg_win_cap + ba_ssn[NUM_TIDS] to struct mt7996_sta
#   mcu.c    : store last TX BA ssn + clamp buf_size to agg_win_cap
#   debugfs.c: agg_win_cap node; write directly replays mt7996_mcu_add_tx_ba(false)->(true)
import sys
TREE = sys.argv[1]
H = TREE + "/mt7996/mt7996.h"
M = TREE + "/mt7996/mcu.c"
D = TREE + "/mt7996/debugfs.c"

def read(p):
    with open(p,"r",encoding="utf-8") as f: return f.read()
def write(p,s):
    with open(p,"w",encoding="utf-8") as f: f.write(s)
def sub(path, old, new, must=1):
    src = read(path); n = src.count(old)
    assert n==must, f"{path}: expected {must}, got {n}"
    write(path, src.replace(old,new)); print(f"  OK {path.split('/')[-1]} ({n}x)")

# 0. CPTCFG fix
sub(D, "#ifdef CONFIG_MAC80211_DEBUGFS",
       "#if defined(CONFIG_MAC80211_DEBUGFS) || defined(CPTCFG_MAC80211_DEBUGFS)")

# 1. struct fields
sub(H, "\tu32 airtime_ac[8];\n",
       "\tu32 airtime_ac[8];\n\tu16 agg_win_cap; /* 0=uncapped, else max TX A-MPDU BA window */\n\tu16 ba_ssn[IEEE80211_NUM_TIDS]; /* last TX BA start seq per tid */\n")

# 2. mcu.c: store ssn + clamp
OLD_MCU = "\tif (enable && !params->amsdu)\n"
NEW_MCU = """\tif (enable)
\t\tmsta->ba_ssn[params->tid] = params->ssn;
\tif (enable && msta->agg_win_cap) {
\t\tparams->buf_size = min_t(u16, params->buf_size,
\t\t\t\t\t msta->agg_win_cap);
\t\tpr_info("aggcap_dbg: add_tx_ba tid=%d cap=%u buf_size=%u ssn=%u\\n",
\t\t\tparams->tid, msta->agg_win_cap, params->buf_size, params->ssn);
\t}
\tif (enable && !params->amsdu)
"""
sub(M, OLD_MCU, NEW_MCU)

# 3a. forward decl
sub(D, "int mt7996_init_debugfs(struct mt7996_dev *dev)",
       "static const struct file_operations fops_agg_win_cap;\n\nint mt7996_init_debugfs(struct mt7996_dev *dev)")
# 3b. register
sub(D, '\tdebugfs_create_file("tx_stats", 0400, dir, dev, &mt7996_tx_stats_fops);',
       '\tdebugfs_create_file("tx_stats", 0400, dir, dev, &mt7996_tx_stats_fops);\n\tdebugfs_create_file("agg_win_cap", 0600, dir, dev, &fops_agg_win_cap);')

FOPS = r'''
#define AGGCAP_MAX_STA 32
#define AGGCAP_MAX_WIN 256

static ssize_t
mt7996_agg_win_cap_read(struct file *file, char __user *ubuf,
			size_t count, loff_t *ppos)
{
	struct mt7996_dev *dev = file->private_data;
	char buf[512];
	int len = 0, i;
	if (!dev) return -EINVAL;
	mutex_lock(&dev->mt76.mutex);
	for (i = 0; i < ARRAY_SIZE(dev->mt76.wcid) && len < (int)sizeof(buf) - 40; i++) {
		struct mt76_wcid *wcid; struct ieee80211_sta *sta; struct mt7996_sta *msta;
		wcid = rcu_dereference_protected(dev->mt76.wcid[i], lockdep_is_held(&dev->mt76.mutex));
		if (!wcid) continue;
		sta = wcid_to_sta(wcid);
		if (!sta) continue;
		msta = (struct mt7996_sta *)sta->drv_priv;
		len += scnprintf(buf + len, sizeof(buf) - len, "%pM %u\n", sta->addr, msta->agg_win_cap);
	}
	mutex_unlock(&dev->mt76.mutex);
	if (!len) len = scnprintf(buf, sizeof(buf), "no stations\n");
	return simple_read_from_buffer(ubuf, count, ppos, buf, len);
}

static ssize_t
mt7996_agg_win_cap_write(struct file *file, const char __user *user_buf, size_t count, loff_t *ppos)
{
	struct mt7996_dev *dev = file->private_data;
	char buf[16];
	unsigned int cap;
	int i, n = 0;
	u16 tid, win;

	if (!dev) return -EINVAL;
	if (count >= sizeof(buf)) return -EINVAL;
	if (copy_from_user(buf, user_buf, count)) return -EFAULT;
	buf[count] = '\0';
	if (kstrtouint(buf, 0, &cap)) return -EINVAL;
	if (cap > AGGCAP_MAX_WIN) return -EINVAL;
	win = cap ? cap : AGGCAP_MAX_WIN; /* 0=uncapped -> restore default window */

	mutex_lock(&dev->mt76.mutex);
	for (i = 0; i < ARRAY_SIZE(dev->mt76.wcid); i++) {
		struct mt76_wcid *wcid; struct ieee80211_sta *sta; struct mt7996_sta *msta;
		wcid = rcu_dereference_protected(dev->mt76.wcid[i], lockdep_is_held(&dev->mt76.mutex));
		if (!wcid) continue;
		sta = wcid_to_sta(wcid);
		if (!sta) continue;
		msta = (struct mt7996_sta *)sta->drv_priv;
		msta->agg_win_cap = cap;
		for (tid = 0; tid < IEEE80211_NUM_TIDS; tid++) {
			struct ieee80211_ampdu_params p;
			if (!test_bit(tid, &msta->wcid.ampdu_state)) continue;
			memset(&p, 0, sizeof(p));
			p.sta = sta;
			p.tid = tid;
			p.ssn = msta->ba_ssn[tid];
			p.buf_size = win;
			p.amsdu = false;
			mt7996_mcu_add_tx_ba(dev, &p, false);
			mt7996_mcu_add_tx_ba(dev, &p, true);
			pr_info("aggcap_dbg: replay sta=%pM tid=%u cap=%u win=%u ssn=%u\n",
				sta->addr, tid, cap, win, p.ssn);
		}
		n++;
	}
	mutex_unlock(&dev->mt76.mutex);
	dev_info(dev->mt76.dev, "agg_win_cap: cap=%u applied to %d station(s)\n", cap, n);
	return count;
}

static const struct file_operations fops_agg_win_cap = {
	.read = mt7996_agg_win_cap_read,
	.write = mt7996_agg_win_cap_write,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};

'''
anchor = "#if defined(CONFIG_MAC80211_DEBUGFS) || defined(CPTCFG_MAC80211_DEBUGFS)"
src = read(D); assert src.count(anchor)==1
write(D, src.replace(anchor, FOPS + anchor))
print("APPLY v4 FINAL DONE")
