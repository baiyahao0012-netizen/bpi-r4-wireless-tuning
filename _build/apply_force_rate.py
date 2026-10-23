#!/usr/bin/env python3
# apply_force_rate.py - per-STA firmware fixed rate via debugfs "force_rate".
import sys, os
T = sys.argv[1]
P = T + "/mt7996/debugfs.c"

def sub(old, new, must=1):
    s = open(P, encoding="utf-8").read()
    assert s.count(old) == must, "anchor count %d" % s.count(old)
    open(P, "w", encoding="utf-8").write(s.replace(old, new, 1))

FUNC = r'''
static ssize_t
mt7996_force_rate_write(struct file *file, const char __user *user_buf,
			size_t count, loff_t *ppos)
{
	struct mt7996_dev *dev = file->private_data;
	struct ra_rate phy = {};
	char buf[128];
	u8 mac[ETH_ALEN];
	unsigned int m0, m1, m2, m3, m4, m5;
	unsigned int mode, bw, mcs, nss, gi, preamble, stbc, ldpc, spe, ltf;
	int i, found = 0, ret = 0;

	if (count >= sizeof(buf))
		return -EINVAL;
	if (copy_from_user(buf, user_buf, count))
		return -EFAULT;
	if (count && buf[count - 1] == '\n')
		buf[count - 1] = '\0';
	else
		buf[count] = '\0';

	if (sscanf(buf, "%x:%x:%x:%x:%x:%x %u %u %u %u %u %u %u %u %u %u",
		   &m0, &m1, &m2, &m3, &m4, &m5,
		   &mode, &bw, &mcs, &nss, &gi, &preamble,
		   &stbc, &ldpc, &spe, &ltf) != 16)
		return -EINVAL;

	mac[0] = m0; mac[1] = m1; mac[2] = m2;
	mac[3] = m3; mac[4] = m4; mac[5] = m5;

	phy.mode = mode;
	phy.bw = bw;
	phy.mcs = mcs;
	phy.nss = nss;
	phy.gi = cpu_to_le16(gi);
	phy.ltf = cpu_to_le16(ltf);
	phy.ldpc = ldpc ? 7 : 0;
	phy.stbc = stbc;
	phy.spe = spe;
	phy.preamble = preamble ? 0 : 1;

	mutex_lock(&dev->mt76.mutex);
	for (i = 0; i < ARRAY_SIZE(dev->mt76.wcid); i++) {
		struct mt76_wcid *wcid;
		struct ieee80211_sta *sta;

		wcid = rcu_dereference_protected(dev->mt76.wcid[i],
						 lockdep_is_held(&dev->mt76.mutex));
		if (!wcid)
			continue;
		sta = wcid_to_sta(wcid);
		if (!sta || !ether_addr_equal(sta->addr, mac))
			continue;
		phy.wlan_idx = cpu_to_le16(wcid->idx);
		ret = mt7996_mcu_set_fixed_rate_ctrl(dev, &phy, 0);
		found = 1;
		break;
	}
	mutex_unlock(&dev->mt76.mutex);

	if (!found)
		return -ENOENT;
	return ret ? ret : count;
}

static const struct file_operations mt7996_force_rate_fops = {
	.write = mt7996_force_rate_write,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};
'''

sub("int mt7996_init_debugfs(struct mt7996_dev *dev)\n{\n\tstruct dentry *dir;\n\n\tdir = mt76_register_debugfs_fops(&dev->mphy, NULL);\n\tif (!dir)\n\t\treturn -ENOMEM;\n",
    FUNC + "\nint mt7996_init_debugfs(struct mt7996_dev *dev)\n{\n\tstruct dentry *dir;\n\n\tdir = mt76_register_debugfs_fops(&dev->mphy, NULL);\n\tif (!dir)\n\t\treturn -ENOMEM;\n")

sub('\tdebugfs_create_file("rf_regval", 0600, dir, dev, &fops_rf_regval);\n',
    '\tdebugfs_create_file("rf_regval", 0600, dir, dev, &fops_rf_regval);\n'
    '\tdebugfs_create_file("force_rate", 0600, dir, dev, &mt7996_force_rate_fops);\n')

print("FORCE_RATE APPLIED")
