#!/usr/bin/env python3
# apply_v2_final.py — v2 patch with CPTCFG_ fix
# FIX: add .open = simple_open to fops_agg_win_cap (sets file->private_data from inode->i_private)
import sys

TREE = sys.argv[1]
H = TREE + "/mt7996/mt7996.h"
M = TREE + "/mt7996/mcu.c"
D = TREE + "/mt7996/debugfs.c"

def read(p):
    with open(p, "r", encoding="utf-8") as f: return f.read()
def write(p, s):
    with open(p, "w", encoding="utf-8") as f: f.write(s)
def sub(path, old, new, must=1):
    src = read(path)
    n = src.count(old)
    assert n == must, f"{path}: expected {must}, got {n}"
    write(path, src.replace(old, new))
    print(f"  OK {path.split('/')[-1]} ({n}x)")

# 0. CPTCFG_ fix
sub(D,
    "#ifdef CONFIG_MAC80211_DEBUGFS",
    "#if defined(CONFIG_MAC80211_DEBUGFS) || defined(CPTCFG_MAC80211_DEBUGFS)")

# 1. mt7996.h field
sub(H, "\tu32 airtime_ac[8];\n",
       "\tu32 airtime_ac[8];\n\tu16 agg_win_cap; /* 0=uncapped; max TX A-MPDU BA window */\n")

# 2. mcu.c clamp
OLD_MCU = "\tif (enable && !params->amsdu)\n"
NEW_MCU = """\tif (enable && msta->agg_win_cap) {
\t\tparams->buf_size = min_t(u16, params->buf_size,
\t\t\t\t\t\t msta->agg_win_cap);
\t\tpr_info("agg_win_cap: sta %pM tid %d buf_size clamped to %u\\n",
\t\t\tparams->sta->addr, params->tid, params->buf_size);
\t}
\tif (enable && !params->amsdu)
"""
sub(M, OLD_MCU, NEW_MCU)

# 3. debugfs.c
# 3a. forward decl
sub(D, "int mt7996_init_debugfs(struct mt7996_dev *dev)",
       "static const struct file_operations fops_agg_win_cap;\n\nint mt7996_init_debugfs(struct mt7996_dev *dev)")
# 3b. register
sub(D, '\tdebugfs_create_file("tx_stats", 0400, dir, dev, &mt7996_tx_stats_fops);',
       '\tdebugfs_create_file("tx_stats", 0400, dir, dev, &mt7996_tx_stats_fops);\n\tdebugfs_create_file("agg_win_cap", 0600, dir, dev, &fops_agg_win_cap);')

# 3c. fops body BEFORE #ifdef — WITH .open = simple_open !!!
FOPS = r'''
#define AGGCAP_MAX_STA 32

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
	struct ieee80211_sta *stas[AGGCAP_MAX_STA];
	char buf[16];
	unsigned int cap;
	int n = 0, i;
	u16 tid;

	if (!dev) return -EINVAL;
	if (count >= sizeof(buf)) return -EINVAL;
	if (copy_from_user(buf, user_buf, count)) return -EFAULT;
	buf[count] = '\0';
	if (kstrtouint(buf, 0, &cap)) return -EINVAL;
	if (cap > 256) return -EINVAL;

	mutex_lock(&dev->mt76.mutex);
	for (i = 0; i < ARRAY_SIZE(dev->mt76.wcid) && n < AGGCAP_MAX_STA; i++) {
		struct mt76_wcid *wcid; struct ieee80211_sta *sta; struct mt7996_sta *msta;
		wcid = rcu_dereference_protected(dev->mt76.wcid[i], lockdep_is_held(&dev->mt76.mutex));
		if (!wcid) continue;
		sta = wcid_to_sta(wcid);
		if (!sta) continue;
		msta = (struct mt7996_sta *)sta->drv_priv;
		msta->agg_win_cap = cap; stas[n++] = sta;
	}
	mutex_unlock(&dev->mt76.mutex);
	for (i = 0; i < n; i++) {
		struct mt7996_sta *msta = (struct mt7996_sta *)stas[i]->drv_priv;
		for (tid = 0; tid < IEEE80211_NUM_TIDS; tid++)
			if (test_bit(tid, &msta->wcid.ampdu_state))
				ieee80211_stop_tx_ba_session(stas[i], tid);
	}
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
src = read(D)
assert src.count(anchor) == 1
src = src.replace(anchor, FOPS + anchor)
write(D, src)
print("  OK fops body with .open=simple_open inserted BEFORE #ifdef")
print("APPLY DONE")
