#!/usr/bin/env python3
# apply_txwi_rate.py - force MT_TXD1_FIXED_RATE for data, using 5G basic table 35 = legacy 6M.
import sys
T=sys.argv[1]
def sub(p, old, new, must=1):
    s=open(p,encoding="utf-8").read()
    assert s.count(old)==must, (p, s.count(old))
    open(p,"w",encoding="utf-8").write(s.replace(old,new,1))

H=T+"/mt7996/mt7996.h"
D=T+"/mt7996/debugfs.c"
M=T+"/mt7996/mac.c"

sub(H, "int mt7996_mcu_set_fixed_rate_table(struct mt7996_phy *phy, u8 table_idx,\n",
       "extern bool mt7996_force_fixed_rate;\n\nint mt7996_mcu_set_fixed_rate_table(struct mt7996_phy *phy, u8 table_idx,\n")

FUNC = r'''
bool mt7996_force_fixed_rate;

static ssize_t
mt7996_force_rate_write(struct file *file, const char __user *user_buf,
			size_t count, loff_t *ppos)
{
	struct mt7996_dev *dev = file->private_data;
	struct mt7996_phy *phy = mt7996_phy2(dev);
	char buf[16];
	u16 rate = 11; /* legacy OFDM 6M */

	if (!phy)
		return -ENODEV;
	if (count >= sizeof(buf))
		return -EINVAL;
	if (copy_from_user(buf, user_buf, count))
		return -EFAULT;
	buf[count] = '\0';
	if (strstr(buf, "he"))
		rate = 0x600; /* HE-MCS0, NSS2, 80MHz */

	mt7996_force_fixed_rate = true;
	mt7996_mcu_set_fixed_rate_table(phy, 35, rate, false);
	dev_info(dev->mt76.dev, "force fixed rate table 35 = 0x%x enabled\n", rate);
	return count;
}

static const struct file_operations mt7996_force_rate_fops = {
	.write = mt7996_force_rate_write,
	.open = simple_open,
	.owner = THIS_MODULE,
	.llseek = default_llseek,
};
'''

sub(D, "int mt7996_init_debugfs(struct mt7996_dev *dev)\n",
       FUNC + "\nint mt7996_init_debugfs(struct mt7996_dev *dev)\n")
sub(D, '\tdebugfs_create_file("rf_regval", 0600, dir, dev, &fops_rf_regval);\n',
       '\tdebugfs_create_file("rf_regval", 0600, dir, dev, &fops_rf_regval);\n'
       '\tdebugfs_create_file("force_rate", 0600, dir, dev, &mt7996_force_rate_fops);\n')

sub(M, "\tif (!ieee80211_is_data(fc) || multicast ||\n\t    info->flags & IEEE80211_TX_CTL_USE_MINRATE)\n\t\tval |= MT_TXD1_FIXED_RATE;\n",
       "\tif (!ieee80211_is_data(fc) || multicast ||\n\t    info->flags & IEEE80211_TX_CTL_USE_MINRATE ||\n\t    mt7996_force_fixed_rate)\n\t\tval |= MT_TXD1_FIXED_RATE;\n")

sub(M, "\tif (is_8023)\n\t\tmt7996_mac_write_txwi_8023(dev, txwi, skb, wcid);\n\telse\n\t\tmt7996_mac_write_txwi_80211(dev, txwi, skb, key);\n\n\tif (txwi[1] & cpu_to_le32(MT_TXD1_FIXED_RATE)) {\n",
       "\tif (is_8023)\n\t\tmt7996_mac_write_txwi_8023(dev, txwi, skb, wcid);\n\telse\n\t\tmt7996_mac_write_txwi_80211(dev, txwi, skb, key);\n\n\tif (mt7996_force_fixed_rate)\n\t\ttxwi[1] |= cpu_to_le32(MT_TXD1_FIXED_RATE);\n\n\tif (txwi[1] & cpu_to_le32(MT_TXD1_FIXED_RATE)) {\n")

print("TXWI_RATE APPLIED")
