#!/usr/bin/env python3
"""Симулятор планирования CPU: FCFS, SJF, SRTF, Priority (вытесняющий, со старением), RR.

Запуск:
    python3 sched.py --algo rr --quantum 3 set1.txt
    python3 sched.py --algo priority --aging 4 set_starve.txt
    python3 sched.py --algo all --quantum 3 set1.txt
"""
import argparse
from collections import deque, namedtuple

Process = namedtuple("Process", "pid arrival burst priority order")
# Интервал: pid == None означает простой CPU
Interval = namedtuple("Interval", "pid start end")


# ---------- чтение данных ----------
def load(path):
    procs = []
    with open(path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            pid, arrival, burst = parts[0], int(parts[1]), int(parts[2])
            priority = int(parts[3]) if len(parts) > 3 else 0  # приоритета нет -> 0
            procs.append(Process(pid, arrival, burst, priority, len(procs)))
    return procs


# ---------- вспомогательное ----------
def _add(intervals, pid, start, end):
    """Добавить интервал, склеивая с предыдущим, если там тот же pid."""
    if intervals and intervals[-1].pid == pid and intervals[-1].end == start:
        intervals[-1] = Interval(pid, intervals[-1].start, end)
    else:
        intervals.append(Interval(pid, start, end))


# ---------- невытесняющие: FCFS и SJF ----------
def _nonpreemptive(procs, pick):
    pending = sorted(procs, key=lambda p: (p.arrival, p.order))
    intervals, t = [], 0
    while pending:
        ready = [p for p in pending if p.arrival <= t]
        if not ready:                       # CPU простаивает до ближайшего прибытия
            nxt = pending[0].arrival
            _add(intervals, None, t, nxt)
            t = nxt
            continue
        p = pick(ready)
        pending.remove(p)
        _add(intervals, p.pid, t, t + p.burst)
        t += p.burst
    return intervals


def fcfs(procs):
    return _nonpreemptive(procs, lambda r: min(r, key=lambda p: (p.arrival, p.order)))


def sjf(procs):
    return _nonpreemptive(procs, lambda r: min(r, key=lambda p: (p.burst, p.arrival, p.order)))


# ---------- вытесняющие по тактам: SRTF и Priority ----------
def _preemptive(procs, mode, aging=0):
    """На КАЖДОМ такте заново выбираем процесс среди пришедших (поэтому вытеснение работает)."""
    rem = {p.pid: p.burst for p in procs}
    prio = {p.pid: p.priority for p in procs}      # текущий (возможно «состаренный») приоритет
    waited = {p.pid: 0 for p in procs}             # сколько тактов ждёт подряд
    intervals, t, current = [], 0, None
    left = len(procs)
    while left:
        ready = [p for p in procs if p.arrival <= t and rem[p.pid] > 0]
        if not ready:
            nxt = min(p.arrival for p in procs if rem[p.pid] > 0)
            _add(intervals, None, t, nxt)
            t, current = nxt, None
            continue

        def key(p):
            value = rem[p.pid] if mode == "srtf" else prio[p.pid]
            # при равенстве: уже работающий остаётся, потом более раннее прибытие
            return (value, 0 if p.pid == current else 1, p.arrival, p.order)

        run = min(ready, key=key)
        _add(intervals, run.pid, t, t + 1)
        rem[run.pid] -= 1
        waited[run.pid] = 0
        for p in ready:                              # остальные готовые ждут
            if p.pid != run.pid:
                waited[p.pid] += 1
                if mode == "priority" and aging and waited[p.pid] >= aging:
                    prio[p.pid] -= 1                 # меньше число = выше приоритет
                    waited[p.pid] = 0
        if rem[run.pid] == 0:
            left -= 1
        current = run.pid
        t += 1
    return intervals


def srtf(procs):
    return _preemptive(procs, "srtf")


def priority(procs, aging=0):
    return _preemptive(procs, "priority", aging)


# ---------- Round Robin ----------
def rr(procs, quantum=3):
    order = sorted(procs, key=lambda p: (p.arrival, p.order))
    rem = {p.pid: p.burst for p in procs}
    queue, intervals, t, i = deque(), [], 0, 0

    def admit(now):                                  # впускаем всех, кто пришёл к моменту now
        nonlocal i
        while i < len(order) and order[i].arrival <= now:
            queue.append(order[i])
            i += 1

    while True:
        admit(t)
        if not queue:
            if i >= len(order):
                break
            _add(intervals, None, t, order[i].arrival)
            t = order[i].arrival
            continue
        p = queue.popleft()
        run = min(quantum, rem[p.pid])
        _add(intervals, p.pid, t, t + run)
        t += run
        rem[p.pid] -= run
        admit(t)                                     # СНАЧАЛА пришедшие в момент t ...
        if rem[p.pid] > 0:
            queue.append(p)                          # ... ПОТОМ вытесненный процесс
    return intervals


ALGOS = {"fcfs": fcfs, "sjf": sjf, "srtf": srtf, "priority": priority, "rr": rr}


def simulate(processes, algorithm, **params):
    """Единая точка входа. Возвращает список интервалов Interval(pid, start, end)."""
    if algorithm not in ALGOS:
        raise ValueError(f"неизвестный алгоритм: {algorithm}")
    return ALGOS[algorithm](processes, **params)


# ---------- метрики ----------
def metrics(procs, intervals):
    first, last = {}, {}
    for iv in intervals:
        if iv.pid is None:
            continue
        first.setdefault(iv.pid, iv.start)
        last[iv.pid] = iv.end
    rows = []
    for p in procs:
        turnaround = last[p.pid] - p.arrival          # оборот = завершение - прибытие
        waiting = turnaround - p.burst                # ожидание = оборот - burst
        response = first[p.pid] - p.arrival           # отклик = первый запуск - прибытие
        rows.append((p.pid, p.arrival, p.burst, p.priority,
                     last[p.pid], waiting, turnaround, response))
    n = len(rows)
    busy = sum(iv.end - iv.start for iv in intervals if iv.pid is not None)
    span = max(iv.end for iv in intervals) - min(p.arrival for p in procs)
    run_seq = [iv.pid for iv in intervals if iv.pid is not None]
    switches = sum(1 for a, b in zip(run_seq, run_seq[1:]) if a != b)
    return {
        "rows": rows,
        "avg_wait": sum(r[5] for r in rows) / n,
        "avg_turn": sum(r[6] for r in rows) / n,
        "avg_resp": sum(r[7] for r in rows) / n,
        "max_wait": max(r[5] for r in rows),
        "cpu": 100.0 * busy / span,
        "switches": switches,
    }


# ---------- вывод ----------
def gantt(intervals):
    return " ".join(f"[{iv.start}-{iv.end}:{iv.pid or 'idle'}]" for iv in intervals)


def print_details(procs, intervals, m):
    print("Диаграмма Ганта:")
    print(gantt(intervals))
    print()
    print(f'{"PID":<6}{"приб.":>6}{"burst":>7}{"прио":>6}{"заверш.":>9}'
          f'{"ожид.":>7}{"оборот":>8}{"отклик":>8}')
    for r in m["rows"]:
        print(f"{r[0]:<6}{r[1]:>6}{r[2]:>7}{r[3]:>6}{r[4]:>9}{r[5]:>7}{r[6]:>8}{r[7]:>8}")
    print()


def print_table(results):
    print(f'{"Алгоритм":<22}{"ожидание":>10}{"оборот":>9}{"отклик":>9}'
          f'{"CPU, %":>9}{"перекл.":>9}{"макс.ожид.":>12}')
    for name, m in results:
        print(f'{name:<22}{m["avg_wait"]:>10.2f}{m["avg_turn"]:>9.2f}{m["avg_resp"]:>9.2f}'
              f'{m["cpu"]:>9.1f}{m["switches"]:>9}{m["max_wait"]:>12}')


def main():
    ap = argparse.ArgumentParser(description="Симулятор планирования CPU")
    ap.add_argument("file", help="файл с процессами: PID arrival burst [priority]")
    ap.add_argument("--algo", default="all",
                    choices=list(ALGOS) + ["all"], help="алгоритм (по умолчанию all)")
    ap.add_argument("--quantum", type=int, default=3, help="квант для RR")
    ap.add_argument("--aging", type=int, default=0,
                    help="старение для priority: каждые N тактов ожидания приоритет растёт (0 = выкл.)")
    ap.add_argument("--no-gantt", action="store_true", help="не печатать диаграмму и таблицу процессов")
    args = ap.parse_args()

    procs = load(args.file)
    todo = list(ALGOS) if args.algo == "all" else [args.algo]
    results = []
    for algo in todo:
        params = {}
        label = algo.upper()
        if algo == "rr":
            params["quantum"] = args.quantum
            label = f"RR (q={args.quantum})"
        if algo == "priority":
            params["aging"] = args.aging
            label = f"PRIORITY (aging={args.aging})" if args.aging else "PRIORITY (без aging)"
        intervals = simulate(procs, algo, **params)
        m = metrics(procs, intervals)
        results.append((label, m))
        if len(todo) == 1 and not args.no_gantt:
            print_details(procs, intervals, m)
    print_table(results)


if __name__ == "__main__":
    main()
