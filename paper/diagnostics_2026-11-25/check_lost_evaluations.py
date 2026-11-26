"""Was any evaluation of arm A lost when the machine ran out of memory on 25 November?

On 25 November, 09:39 to 09:42, the first scoring run of the floor test used up the memory the
system could promise while 30 runs of arm A were still going (README, "A lesson about
memory"). An evaluation of arm A is one run of the 2013 simulator. Had one been lost, the search
would have gone on with the score the 2013 code gives a simulation that left no result, 0.001,
and nothing else would show it.

Arm A records the score of every body of every generation (`gen_NNN.json`, 30 scores each; in
its mode the whole population is evaluated in every generation). This counts the scores that are
exactly 0.001 (no result) or exactly 0.0001 (what the 2013 code gives anything unusable), in the
whole arm and in the generations written around the incident. It reads no other score and
reports only counts, so it can be run before the arm is analysed.

A run that had crashed instead would have been continued by the launcher and logged; the
launcher's log has no such line.

usage:
    python paper/diagnostics_2026-11-25/check_lost_evaluations.py
        written next to this file: lost_evaluations_check.json
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)

from src.evolution import cheney2013 as c13                   # noqa: E402

ARM, SEEDS, GENERATIONS = 'armA', range(1, 36), 1000
WINDOWS = (('the three hours before', '2026-11-25 06:00', '2026-11-25 08:50'),
           ('around the incident', '2026-11-25 08:50', '2026-11-25 10:15'),
           ('the three hours after', '2026-11-25 10:15', '2026-11-25 13:00'))


def moment(text):
    return time.mktime(time.strptime(text, '%Y-%m-%d %H:%M'))


def empty():
    return {'generations': 0, 'scores': 0, 'no_result': 0, 'unusable': 0}


def main():
    whole = empty()
    windows = [dict(empty(), name=name, start=a, end=b) for name, a, b in WINDOWS]
    seeds_touched = {}
    for seed in SEEDS:
        folder = os.path.join(ROOT, 'results', f'{ARM}_s{seed}')
        for g in range(1, GENERATIONS + 1):
            path = os.path.join(folder, f'gen_{g:03d}.json')
            with open(path, encoding='utf-8') as f:
                scores = json.load(f)['fitnesses']
            lost = sum(1 for x in scores if x == c13.MISSING_FITNESS)
            unusable = sum(1 for x in scores if x == c13.FLOOR_FITNESS)
            written = os.path.getmtime(path)
            for box in [whole] + [w for w in windows if moment(w['start']) <= written < moment(w['end'])]:
                box['generations'] += 1
                box['scores'] += len(scores)
                box['no_result'] += lost
                box['unusable'] += unusable
            if lost or unusable:
                seeds_touched[seed] = seeds_touched.get(seed, 0) + lost + unusable
    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'arm': ARM, 'no_result_score': c13.MISSING_FITNESS,
              'unusable_score': c13.FLOOR_FITNESS, 'whole_arm': whole, 'windows': windows,
              'seeds_with_such_a_score': seeds_touched}
    with open(os.path.join(HERE, 'lost_evaluations_check.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    print(f"{'':28} {'generations':>11} {'scores':>9} {'no result':>10} {'unusable':>9}")
    for name, box in [('the whole arm', whole)] + [(f"{w['name']}", w) for w in windows]:
        print(f"{name:28} {box['generations']:11d} {box['scores']:9d} {box['no_result']:10d} {box['unusable']:9d}")
    print(f"Runs with such a score: {len(seeds_touched)} of {len(SEEDS)}.")


if __name__ == '__main__':
    main()
