# -*- coding: utf-8 -*-
import csv, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

xs, vo, bk = [], [], []
with open(r'_work_final/ac_mix_final.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        xs.append(float(row['elapsed_s'])); vo.append(float(row['vo_mbps'])); bk.append(float(row['bk_mbps']))

plt.figure(figsize=(10, 4.6), dpi=160)
plt.plot(xs, vo, label='VO (SO_PRIORITY=262)', linewidth=1.6)
plt.plot(xs, bk, label='BK (SO_PRIORITY=257)', linewidth=1.6)
plt.axvline(6, color='gray', linestyle='--', linewidth=0.9)
plt.axvline(12, color='gray', linestyle='--', linewidth=0.9)
plt.text(6.1, max(max(vo), max(bk))*0.92, 'VO aggressive', fontsize=8, color='gray')
plt.text(12.1, max(max(vo), max(bk))*0.92, 'BK aggressive', fontsize=8, color='gray')
plt.xlabel('Time (s)')
plt.ylabel('Downlink throughput (Mbit/s)')
plt.title('BPI-R4 5G AP: VO vs BK mixed-AC competition (100 ms bins)')
plt.legend(loc='center right')
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig(r'_work_final/ac_mix_timeline.png')
print('saved')
