#!/usr/bin/env python3
"""Генерация set2.txt, set3.txt и set_starve.txt (seed фиксирован)."""
import random
random.seed(7)

# set2: 20 CPU-bound процессов, длинные бёрсты 20..60
with open("set2.txt", "w") as f:
    t = 0
    for i in range(1, 21):
        t += random.randint(0, 4)
        f.write(f"P{i} {t} {random.randint(20, 60)} {random.randint(1, 5)}\n")

# set3: 19 коротких (1..6) + один длинный P1 (burst 100)
with open("set3.txt", "w") as f:
    f.write("P1 0 100 3\n")
    t = 0
    for i in range(2, 21):
        t += random.randint(1, 3)
        f.write(f"P{i} {t} {random.randint(1, 6)} {random.randint(1, 5)}\n")

# set_starve: P1 с плохим приоритетом (9) + постоянный поток коротких с приоритетом 1
with open("set_starve.txt", "w") as f:
    f.write("P1 0 5 9\n")
    for i in range(2, 22):
        f.write(f"P{i} {(i - 2) * 3 + 1} 4 1\n")   # каждые 3 такта приходит процесс на 4 такта
