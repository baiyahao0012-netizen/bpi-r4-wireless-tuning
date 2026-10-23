#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 BPI-R4 mt76 MCS 速率掩码补丁项目交接文档
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()

# 设置默认字体
style = doc.styles['Normal']
style.font.name = '宋体'
style.font.size = Pt(12)
style._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

# 标题
title = doc.add_heading('BPI-R4 mt76 MCS 速率掩码补丁项目交接文档', 0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ========== 1. 项目背景与目标 ==========
doc.add_heading('1. 项目背景与目标', level=1)

doc.add_heading('1.1 课题背景', level=2)
doc.add_paragraph('本项目属于无线优化课题的一部分，核心问题：mt7996 芯片使用硬件固件速率控制（Firmware RC），而非 minstrel_ht 软件 RC。这导致标准的 `iw dev set bitrates` 命令完全不生效——host 设置的速率位图根本不会被固件消费。')

doc.add_heading('1.2 项目目标', level=2)
doc.add_paragraph('修改 mt76 驱动源码，通过 debugfs 节点实时强制锁定 MCS 速率。具体方案：在 mt76_connac_mcu.c 的 sta_tlv() 函数里，host 发送 sta_rec_ra_info TLV 给固件后，用 force_mcs 值覆盖 rx_mcs_bitmask 字段，让固件只使用指定的 MCS 速率发送。')

doc.add_heading('1.3 核心技术难点', level=2)
p = doc.add_paragraph()
p.add_run('• mt76 驱动分为三个 ko：mt76.ko、mt76-connac-lib.ko、mt7996e.ko，跨模块变量导出容易出问题\n').bold = False
p.add_run('• 不能修改 struct mt76_dev 的字段（会导致后续字段偏移错位，MCU 通信全超时）\n')
p.add_run('• 不能用 debugfs_create_u8(&var) 直接传变量地址（链接器不对导出符号做本地重定位，运行时报 Unknown symbol）\n')
p.add_run('• 热加载驱动时必须先 down 掉所有无线接口，否则 rmmod 失败')

# ========== 2. 硬件与环境 ==========
doc.add_heading('2. 硬件与环境', level=1)

doc.add_heading('2.1 板子硬件', level=2)
p = doc.add_paragraph()
p.add_run('• 型号：Banana Pi BPI-R4 PoE\n')
p.add_run('• WiFi 芯片：MT7996（三频：2.4G / 5G / 6G）\n')
p.add_run('• 系统：OpenWrt 24.10，内核 6.6.73\n')
p.add_run('• 网口：eth0（WAN/LAN 复用）、eth1（2.5G LAN）、eth2（10G SFP）')

doc.add_heading('2.2 开发电脑环境', level=2)
p = doc.add_paragraph()
p.add_run('• 操作系统：Windows 11\n')
p.add_run('• 开发环境：WSL（Ubuntu），里面有 OpenWrt SDK\n')
p.add_run('• 有线连接：电脑有线网口 ↔ 板子 lan1 口（直连）\n')
p.add_run('• 板子 br-lan 手动加 IP：192.168.240.1/24\n')
p.add_run('• SSH：WSL 里 `ssh root@192.168.240.1`，密码 `w`，已配置免密 key')

doc.add_heading('2.3 SDK 路径（WSL 内）', level=2)
p = doc.add_paragraph()
p.add_run('SDK 根目录：').bold = True
p.add_run('/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/\n')
p.add_run('mt76 源码目录：').bold = True
p.add_run('build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/\n')
p.add_run('源码包：').bold = True
p.add_run('dl/mt76-2025.01.14~8e4f72b6.tar.zst（可用 `tar --use-compress-program=unzstd` 解压）')

# ========== 3. 板子控制方法（重点） ==========
doc.add_heading('3. 板子控制方法（重点！）', level=1)

doc.add_heading('3.1 串口控制', level=2)
doc.add_paragraph('通过 USB 转串口连接板子的调试串口，波特率 115200。串口是最可靠的控制方式，SSH 断了也能通过串口操作。')
p = doc.add_paragraph()
p.add_run('常用串口命令：\n').bold = True
p.add_run('• 重启板子：`reboot -f`（普通 reboot 会被系统禁止）\n')
p.add_run('• 手动加 IP：`ip addr add 192.168.240.1/24 dev br-lan`（重启后默认没有这个 IP，必须手动加才能 SSH）\n')
p.add_run('• 查看无线接口：`iw dev`\n')
p.add_run('• 查看 dmesg：`dmesg | tail -20`')

doc.add_heading('3.2 SSH 控制', level=2)
doc.add_paragraph('前提：板子已经手动加了 192.168.240.1/24 的 IP。')
p = doc.add_paragraph()
p.add_run('在 WSL 里执行：\n').bold = True
p.add_run('```bash\nssh root@192.168.240.1\n```\n')
p.add_run('注意：\n').bold = True
p.add_run('• scp 必须加 `-O` 参数（板端 dropbear 没有 sftp-server）：\n')
p.add_run('  `scp -O file root@192.168.240.1:/tmp/`\n')
p.add_run('• 远程执行命令：\n')
p.add_run('  `ssh root@192.168.240.1 "command here"`')

doc.add_heading('3.3 无线配置', level=2)
p = doc.add_paragraph()
p.add_run('板子有三个 radio：\n').bold = True
p.add_run('• radio0：2.4GHz，AP 模式，SSID `BPI-R4`，密码 `12345678`\n')
p.add_run('• radio1：5GHz，AP 模式，SSID `BPI-R4-5G`，密码 `12345678`\n')
p.add_run('• radio2：6GHz，AP 模式，SSID `BPI-R4-6G`，密码 `12345678`\n')
p.add_run('• sta0：station 模式，连 `DianGroup103`，密码 `DianGroup2002`（实验室 WiFi）\n\n')
p.add_run('配置命令：\n').bold = True
p.add_run('```bash\nuci set wireless.default_radio0.disabled=0  # 启用 2.4G AP\nuci commit wireless\nwifi up\n```')

doc.add_heading('3.4 驱动热加载/卸载', level=2)
doc.add_paragraph('不用重启板子，直接热加载新编译的 ko。注意：必须先 down 掉所有无线接口，否则 rmmod 失败。')
p = doc.add_paragraph()
p.add_run('完整热加载流程：\n').bold = True
p.add_run('```bash\n# 1. down 掉所有无线接口\nip link set phy3.0-ap0 down\nip link set phy3.1-ap0 down\nip link set phy3.2-ap0 down\n\n# 2. 卸载旧驱动\nrmmod mt7996e\nrmmod mt76-connac-lib\nrmmod mt76\n\n# 3. 加载新驱动（从 /tmp/ 加载）\ninsmod /tmp/mt76.ko\ninsmod /tmp/mt76-connac-lib.ko\ninsmod /tmp/mt7996e.ko\n\n# 4. 等 2 秒，查 phy 编号（每次热加载后编号会变！）\nls /sys/kernel/debug/ieee80211/\n```')
p.add_run('注意：每次热加载后 phy 编号会递增（phy0 → phy1 → phy2 → phy3...），必须重新查。')

doc.add_heading('3.5 编译部署完整流程', level=2)
p = doc.add_paragraph()
p.add_run('步骤 1：修改源码（在 WSL 里）\n').bold = True
p.add_run('源码路径：build_dir/.../mt76-2025.01.14~8e4f72b6/\n\n')
p.add_run('步骤 2：编译\n').bold = True
p.add_run('```bash\ncd /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/\nmake package/kernel/mt76/compile V=s -j4\n```\n')
p.add_run('注意：tools/mt76-test 缺 unl.h 会报错，但不影响内核 ko 编译，忽略即可。\n\n')
p.add_run('步骤 3：部署到板子\n').bold = True
p.add_run('```bash\ncd build_dir/.../mt76-2025.01.14~8e4f72b6/\nscp -O mt76.ko mt76-connac-lib.ko mt7996/mt7996e.ko root@192.168.240.1:/tmp/\n```\n\n')
p.add_run('步骤 4：热加载（见 3.4）\n').bold = True

# ========== 4. 补丁方案演进历史 ==========
doc.add_heading('4. 补丁方案演进历史（v1 ~ v6）', level=1)
doc.add_paragraph('经过多轮试错，最终 v6 方案成功创建了 force_mcs debugfs 节点。以下是所有失败方案的记录，避免下一个 agent 再踩坑。')

doc.add_heading('4.1 v1 / v2：变量定义位置跨模块不对', level=2)
p = doc.add_paragraph()
p.add_run('失败原因：变量定义在 mt7996e.ko 里，但 mt76-connac-lib.ko 要引用，modpost 报错 Unknown symbol。\n')
p.add_run('结论：跨模块变量必须放在最底层的 mt76.ko 里，上层模块才能引用。')

doc.add_heading('4.2 v3：变量放 connac_mcu.c + EXPORT_SYMBOL', level=2)
p = doc.add_paragraph()
p.add_run('失败原因：modprobe 直接 Segmentation fault，循环依赖 connac-lib ↔ mt76。\n')
p.add_run('结论：不能把变量放在 connac-lib 里然后又被 mt76 引用，会形成循环依赖。')

doc.add_heading('4.3 v4：变量放 debugfs.c + EXPORT_SYMBOL_GPL + debugfs_create_u8(&var)', level=2)
p = doc.add_paragraph()
p.add_run('失败原因：加载成功但运行时报 Unknown symbol（链接器不对导出符号做本地重定位）。\n')
p.add_run('结论：不能用 debugfs_create_u8(&var) 直接传导出变量的地址，因为内核链接器对 EXPORT_SYMBOL 的变量不做本地重定位。')

doc.add_heading('4.4 v5：改 struct mt76_dev 加字段', level=2)
p = doc.add_paragraph()
p.add_run('失败原因：struct 字段偏移错位，MCU 通信全超时（即使加在结构体末尾也有问题）。\n')
p.add_run('结论：绝对不能改 struct mt76_dev 的布局！这会导致所有后续字段偏移错误，驱动直接瘫痪。')

doc.add_heading('4.5 v6：全局变量 + 自定义 fops 方案（成功！）', level=2)
p = doc.add_paragraph()
p.add_run('最终成功的方案：\n').bold = True
p.add_run('• 变量定义在 debugfs.c（mt76.ko）里，加 EXPORT_SYMBOL_GPL\n')
p.add_run('• debugfs 节点用自定义 fops（simple_attr），show/write 函数内部读写全局变量\n')
p.add_run('• connac_mcu.c 里 extern 引用全局变量，sta_tlv() 里覆盖 rx_mcs_bitmask\n')
p.add_run('• 不改 struct mt76_dev，不改 mt76.h，mt7996e.ko 用原版布局')

# ========== 5. 当前补丁状态（v6 最终版） ==========
doc.add_heading('5. 当前补丁状态（v6 最终版）', level=1)

doc.add_heading('5.1 debugfs.c 修改内容', level=2)
p = doc.add_paragraph()
p.add_run('文件位置：mt76-2025.01.14~8e4f72b6/debugfs.c\n\n')
p.add_run('修改点 1：文件开头（#include 之后）\n').bold = True
p.add_run('```c\nu8 mt76_force_mcs = 0xFF;  // 默认 0xFF = 不限制 MCS\nEXPORT_SYMBOL_GPL(mt76_force_mcs);\n\nstatic int force_mcs_show(void *data, u64 *val)\n{\n\t*val = mt76_force_mcs;\n\treturn 0;\n}\n\nstatic int force_mcs_write(void *data, u64 val)\n{\n\tmt76_force_mcs = (u8)val;\n\treturn 0;\n}\n\nDEFINE_DEBUGFS_ATTRIBUTE(force_mcs_fops, force_mcs_show, force_mcs_write, "%llu\\n");\n```\n\n')
p.add_run('修改点 2：mt76_register_debugfs_fops() 函数里，otp blob 之后\n').bold = True
p.add_run('```c\nif (dev->otp.data)\n\tdebugfs_create_blob("otp", 0400, dir, &dev->otp);\ndebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);  // ← 加这行\n```')

doc.add_heading('5.2 mt76_connac_mcu.c 修改内容', level=2)
p = doc.add_paragraph()
p.add_run('文件位置：mt76-2025.01.14~8e4f72b6/mt76_connac_mcu.c\n\n')
p.add_run('修改点 1：文件开头（最后一个 #include 之后）\n').bold = True
p.add_run('```c\nextern u8 mt76_force_mcs;\n```\n\n')
p.add_run('修改点 2：sta_tlv() 函数里，memcpy(rx_mcs_bitmask) 结束之后\n').bold = True
p.add_run('```c\nif (sta->deflink.ht_cap.ht_supported)\n\tmemcpy(ra_info->rx_mcs_bitmask,\n\t\t   sta->deflink.ht_cap.mcs.rx_mask,\n\t\t   HT_MCS_MASK_NUM);\n\nif (mt76_force_mcs < 8) {\n\tmemset(ra_info->rx_mcs_bitmask, 0, HT_MCS_MASK_NUM);\n\tra_info->rx_mcs_bitmask[mt76_force_mcs] = 0xff;\n\tprintk("mt76: FORCE MCS%u\\n", mt76_force_mcs);\n}\n```')

doc.add_heading('5.3 mt76.h 状态', level=2)
doc.add_paragraph('已恢复原版，无 force_mcs 字段。v5 改 struct 的方案已废弃。')

# ========== 6. 当前板端状态 ==========
doc.add_heading('6. 当前板端状态', level=1)

doc.add_heading('6.1 已部署的 ko', level=2)
p = doc.add_paragraph()
p.add_run('三个 ko 已部署到 /lib/modules/6.6.73/：\n').bold = True
p.add_run('• mt76.ko（带 force_mcs 补丁）\n')
p.add_run('• mt76-connac-lib.ko（带 extern 引用）\n')
p.add_run('• mt7996e.ko（原版，未修改）')

doc.add_heading('6.2 force_mcs 节点', level=2)
p = doc.add_paragraph()
p.add_run('路径：').bold = True
p.add_run('/sys/kernel/debug/ieee80211/phy3/mt76/force_mcs\n')
p.add_run('当前值：').bold = True
p.add_run('255（0xFF = 不限制 MCS）\n')
p.add_run('使用方法：').bold = True
p.add_run('```bash\necho 0 > force_mcs   # 强制锁 MCS0（最低速）\necho 7 > force_mcs   # 强制锁 MCS7\ncat force_mcs        # 查看当前值\n```\n')
p.add_run('注意：每次热加载后 phy 编号会变（phy0 → phy1 → phy2 → phy3...），必须重新查路径。')

doc.add_heading('6.3 无线接口状态', level=2)
p = doc.add_paragraph()
p.add_run('• AP 模式正常：2.4G / 5G / 6G AP 都能正常发 beacon\n')
p.add_run('• station 模式异常：连 DianGroup103 时有 MCU timeout（见第 7 节）')

# ========== 7. 已知问题与死路 ==========
doc.add_heading('7. 已知问题与死路（已验证不可行）', level=1)

doc.add_heading('7.1 iw set bitrates 双模式完全不生效', level=2)
p = doc.add_paragraph()
p.add_run('现象：`iw dev phy0.1-sta0 set bitrates legacy-2.4 6` 设置后，实际速率不变。\n')
p.add_run('原因：mt7996 用硬件固件 RC，不消费 host 端的速率位图。\n')
p.add_run('结论：这条路死了，必须改驱动源码让 host 主动把速率掩码发给固件。')

doc.add_heading('7.2 minstrel_ht debugfs fixed_rate_idx 未注册', level=2)
p = doc.add_paragraph()
p.add_run('现象：找不到 minstrel_ht 的 fixed_rate_idx 节点。\n')
p.add_run('原因：mt7996 用固件 RC，不是 minstrel_ht 软件 RC。\n')
p.add_run('结论：这条路死了。')

doc.add_heading('7.3 station 模式 MCU timeout（核心未解决问题）', level=2)
p = doc.add_paragraph()
p.add_run('现象：\n').bold = True
p.add_run('• `ip link set phy0.1-sta0 up` 超时\n')
p.add_run('• dmesg 报错：`Message 001a0034 (seq 15) timeout`\n')
p.add_run('• dmesg 报错：`Message 00120012 (seq 1) timeout`\n\n')
p.add_run('已验证：\n').bold = True
p.add_run('• 干净源码（无任何补丁）编译的 ko 也有同样问题\n')
p.add_run('• AP 模式完全正常，只有 station 模式有问题\n')
p.add_run('• 说明问题不在 force_mcs 补丁，而在 SDK 编译环境或源码包本身\n\n')
p.add_run('MCU 命令含义：\n').bold = True
p.add_run('• 0x12 = MCU_UNI_CMD_RX_HDR_TRANS（接收头转换）\n')
p.add_run('• 0x1a 命令含义未确认')

doc.add_heading('7.4 热加载注意事项', level=2)
p = doc.add_paragraph()
p.add_run('• 必须先 down 掉所有无线接口才能 rmmod，否则 rmmod 失败\n')
p.add_run('• 热加载后 phy 编号会递增（phy0 → phy1 → phy2...），必须重新查\n')
p.add_run('• 远程 reboot 被系统禁止，要用 `reboot -f`（只能在串口执行）\n')
p.add_run('• 热加载不会断 SSH（有线网口和 mt76 无关）')

doc.add_heading('7.5 编译注意事项（踩过的坑）', level=2)
p = doc.add_paragraph()
p.add_run('• tools/mt76-test 缺 unl.h，编译前必须 `mv tools tools.bak`\n')
p.add_run('• 改完源码后必须删除对应的 .o 文件强制重编：`rm -f debugfs.o mt76_connac_mcu.o mt76.ko`\n')
p.add_run('• 必须走 OpenWrt make 流程（自动带 ARCH=arm64 和交叉编译器）\n')
p.add_run('• PowerShell 调 wsl bash 复杂转义会出问题，python 脚本写到 D:\\ 下用 `wsl python3 "/mnt/d/..."` 执行\n')
p.add_run('• scp 必须加 `-O` 参数（板端 dropbear 无 sftp-server）')

# ========== 8. 待完成工作 ==========
doc.add_heading('8. 待完成工作（下一个 agent 接手）', level=1)

tasks = [
    '解决 station 模式 MCU timeout 问题（Message 001a0034 / 00120012）——这是当前最大的阻塞问题',
    '完成 iperf3 打流测试，验证 force_mcs 的实际效果（设 force_mcs=0 看吞吐率是否降到最低）',
    '将补丁代码提交到 GitHub 私有仓库（https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning）',
    '完成实验报告，写入 MCS 锁速的实测数据',
]

for i, task in enumerate(tasks, 1):
    p = doc.add_paragraph()
    p.add_run(f'☐ {i}. {task}').bold = False

# ========== 9. 关键文件路径 ==========
doc.add_heading('9. 关键文件路径', level=1)

p = doc.add_paragraph()
p.add_run('Windows 工作目录：').bold = True
p.add_run('D:\\Desktop\\AI 辅助对话\\\n\n')
p.add_run('补丁脚本：\n').bold = True
p.add_run('• _work_timeline/clean_patch.py：干净补丁脚本（从原版源码打 force_mcs 补丁）\n')
p.add_run('• _work_timeline/fix_connac_patch_v2.py：修复 connac_mcu.c 补丁位置\n\n')
p.add_run('WSL 源码目录：\n').bold = True
p.add_run('/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/\n\n')
p.add_run('板端 ko 路径：\n').bold = True
p.add_run('/lib/modules/6.6.73/mt76.ko\n')
p.add_run('/lib/modules/6.6.73/mt76-connac-lib.ko\n')
p.add_run('/lib/modules/6.6.73/mt7996e.ko')

# ========== 10. GitHub 仓库 ==========
doc.add_heading('10. GitHub 仓库', level=1)
p = doc.add_paragraph()
p.add_run('地址：').bold = True
p.add_run('https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning（私有仓库）\n')
p.add_run('状态：').bold = True
p.add_run('初始提交已推送，补丁代码尚未推送')

# ========== 保存 ==========
output_path = r'D:\Desktop\AI 辅助对话\BPI-R4_mt76_MCS补丁项目交接文档.docx'
doc.save(output_path)
print(f'Done! Saved to {output_path}')
