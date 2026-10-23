#!/usr/bin/env python3
# apply_aplus.py - A+ per-STA frame-token bucket in mt76 host TXQ scheduler.
# Keeps ieee80211_next_txq()/ieee80211_return_txq() lifecycle; only adds a
# per-WCID budget check before mt76_txq_send_burst().
import sys, os

TREE = sys.argv[1]
H = TREE + "/mt76.h"
TX = TREE + "/tx.c"
D = TREE + "/debugfs.c"

def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def sub(path, old, new, must=1):
    s = read(path)
    n = s.count(old)
    assert n == must, "%s: expected %d, got %d" % (path, must, n)
    write(path, s.replace(old, new, 1))
    print("  OK", os.path.basename(path), n)

# 1) per-WCID fields
sub(H, "\tstruct list_head poll_list;\n\n\tstruct mt76_wcid *def_wcid;\n",
       "\tstruct list_head poll_list;\n\n\tstruct mt76_wcid *def_wcid;\n\n"
       "\t/* A+ per-STA frame-token bucket (0 = disabled/unlimited) */\n"
       "\tu32 tx_weight;\n"
       "\ts32 tx_tokens;\n"
       "\tunsigned long tx_token_jiffies;\n"
       "\n#define MT76_STA_TOKEN_QUANTUM\t512\n")

# 2) tx.c: helper + token gate
sub(TX, '#include "mt76.h"\n', '#include "mt76.h"\n#include <linux/jiffies.h>\n')

HELPER = r'''
#define MT76_STA_TOKEN_MAX	8192

static void mt76_wcid_refill_tokens(struct mt76_wcid *wcid)
{
	unsigned long now = jiffies;

	if (!wcid->tx_weight)
		return;

	if (!wcid->tx_token_jiffies) {
		wcid->tx_token_jiffies = now;
		return;
	}

	if (time_before(now, wcid->tx_token_jiffies +
			     msecs_to_jiffies(10)))
		return;

	wcid->tx_tokens += wcid->tx_weight * MT76_STA_TOKEN_QUANTUM;
	if (wcid->tx_tokens > MT76_STA_TOKEN_MAX)
		wcid->tx_tokens = MT76_STA_TOKEN_MAX;
	wcid->tx_token_jiffies = now;
}

static bool mt76_wcid_token_ok(struct mt76_wcid *wcid)
{
	if (!wcid->tx_weight)
		return true;

	mt76_wcid_refill_tokens(wcid);
	return wcid->tx_tokens > 0;
}
'''

sub(TX, "static int\nmt76_txq_schedule_list(struct mt76_phy *phy, enum mt76_txq_id qid)\n",
       HELPER + "\nstatic int\nmt76_txq_schedule_list(struct mt76_phy *phy, enum mt76_txq_id qid)\n")

sub(TX, "\tstruct mt76_queue *q;\n\tint ret = 0;\n",
       "\tstruct mt76_queue *q;\n\tint ret = 0;\n\tint skipped = 0;\n")

sub(TX, "\t\tif (test_bit(MT76_RESET, &phy->state) || phy->offchannel)\n\t\t\tcontinue;\n\n\t\tq = phy->q_tx[qid];\n",
       "\t\tif (test_bit(MT76_RESET, &phy->state) || phy->offchannel)\n\t\t\tcontinue;\n\n"
       "\t\tif (!mt76_wcid_token_ok(wcid)) {\n"
       "\t\t\tieee80211_return_txq(phy->hw, txq, false);\n"
       "\t\t\tif (++skipped > 64)\n"
       "\t\t\t\tbreak;\n"
       "\t\t\tcontinue;\n"
       "\t\t}\n"
       "\t\tskipped = 0;\n\n"
       "\t\tq = phy->q_tx[qid];\n")

sub(TX, "\t\tif (!mt76_txq_stopped(q))\n\t\t\tn_frames = mt76_txq_send_burst(phy, q, mtxq, wcid);\n\n\t\tieee80211_return_txq(phy->hw, txq, false);\n",
       "\t\tif (!mt76_txq_stopped(q))\n\t\t\tn_frames = mt76_txq_send_burst(phy, q, mtxq, wcid);\n\n"
       "\t\tif (n_frames > 0 && wcid->tx_weight)\n"
       "\t\t\twcid->tx_tokens -= n_frames;\n\n"
       "\t\tieee80211_return_txq(phy->hw, txq, false);\n")

# 3) debugfs: per-MAC weight control
sub(D, '#include "mt76.h"\n', '#include "mt76.h"\n#include <linux/etherdevice.h>\n#include <linux/seq_file.h>\n#include <linux/jiffies.h>\n')

DBG = r'''
static int mt76_sta_weight_show(struct seq_file *s, void *data)
{
	struct mt76_dev *dev = s->private;
	int i;

	mutex_lock(&dev->mutex);
	for (i = 0; i < ARRAY_SIZE(dev->wcid); i++) {
		struct mt76_wcid *wcid;
		struct ieee80211_sta *sta;

		wcid = rcu_dereference_protected(dev->wcid[i],
						 lockdep_is_held(&dev->mutex));
		if (!wcid)
			continue;
		sta = wcid_to_sta(wcid);
		if (!sta)
			continue;
		seq_printf(s, "%pM %u %d\n", sta->addr,
			   wcid->tx_weight, wcid->tx_tokens);
	}
	mutex_unlock(&dev->mutex);
	return 0;
}

static int mt76_sta_weight_open(struct inode *inode, struct file *file)
{
	return single_open(file, mt76_sta_weight_show, inode->i_private);
}

static ssize_t
mt76_sta_weight_write(struct file *file, const char __user *buf,
		      size_t count, loff_t *ppos)
{
	struct seq_file *s = file->private_data;
	struct mt76_dev *dev = s->private;
	unsigned int m0, m1, m2, m3, m4, m5, weight;
	char tmp[64];
	u8 mac[ETH_ALEN];
	int i, found = 0;

	if (count >= sizeof(tmp))
		return -EINVAL;
	if (copy_from_user(tmp, buf, count))
		return -EFAULT;
	tmp[count] = '\0';

	if (sscanf(tmp, "%x:%x:%x:%x:%x:%x %u",
		   &m0, &m1, &m2, &m3, &m4, &m5, &weight) != 7)
		return -EINVAL;
	mac[0] = m0; mac[1] = m1; mac[2] = m2;
	mac[3] = m3; mac[4] = m4; mac[5] = m5;
	if (weight > 64)
		return -EINVAL;

	mutex_lock(&dev->mutex);
	for (i = 0; i < ARRAY_SIZE(dev->wcid); i++) {
		struct mt76_wcid *wcid;
		struct ieee80211_sta *sta;

		wcid = rcu_dereference_protected(dev->wcid[i],
						 lockdep_is_held(&dev->mutex));
		if (!wcid)
			continue;
		sta = wcid_to_sta(wcid);
		if (!sta || !ether_addr_equal(sta->addr, mac))
			continue;
		wcid->tx_weight = weight;
		wcid->tx_tokens = weight * MT76_STA_TOKEN_QUANTUM;
		wcid->tx_token_jiffies = jiffies;
		found = 1;
	}
	mutex_unlock(&dev->mutex);

	return found ? count : -ENOENT;
}

static const struct file_operations mt76_sta_weight_fops = {
	.open = mt76_sta_weight_open,
	.read = seq_read,
	.write = mt76_sta_weight_write,
	.llseek = seq_lseek,
	.release = single_release,
};
'''

sub(D, 'static int\nmt76_reg_set(void *data, u64 val)\n', DBG + '\nstatic int\nmt76_reg_set(void *data, u64 val)\n')

sub(D, '\tif (dev->otp.data)\n\t\tdebugfs_create_blob("otp", 0400, dir, &dev->otp);\n',
       '\tif (dev->otp.data)\n\t\tdebugfs_create_blob("otp", 0400, dir, &dev->otp);\n'
       '\tdebugfs_create_file("sta_weight", 0600, dir, dev, &mt76_sta_weight_fops);\n')

print("A+ APPLIED")
