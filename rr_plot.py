#!/usr/bin/env python3
"""График для RR на set2: квант 1..10 -> среднее ожидание и число переключений."""
import matplotlib
matplotlib.use("Agg")                      # без окна, только файл
import matplotlib.pyplot as plt
from sched import load, simulate, metrics

procs = load("set2.txt")
quanta = list(range(1, 11))
waits, switches = [], []
print(f'{"q":>3}{"ср.ожидание":>14}{"переключений":>14}')
for q in quanta:
    m = metrics(procs, simulate(procs, "rr", quantum=q))
    waits.append(m["avg_wait"])
    switches.append(m["switches"])
    print(f'{q:>3}{m["avg_wait"]:>14.2f}{m["switches"]:>14}')

fig, ax1 = plt.subplots(figsize=(8, 4.5))
ax1.plot(quanta, waits, "o-", color="#1f77b4")
ax1.set_xlabel("Квант q")
ax1.set_ylabel("Среднее ожидание", color="#1f77b4")
ax2 = ax1.twinx()
ax2.plot(quanta, switches, "s--", color="#d62728")
ax2.set_ylabel("Число переключений", color="#d62728")
ax1.set_xticks(quanta)
ax1.grid(alpha=0.3)
plt.title("Round Robin на set2: влияние кванта")
fig.tight_layout()
fig.savefig("rr_plot.png", dpi=150)
print("Сохранено: rr_plot.png")
