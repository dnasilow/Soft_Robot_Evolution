"""The transfer outcome of arm D (PROTOCOL.md, sections 4 and 9.7): its final champions, which
were evolved in this project's MuJoCo engine, scored in the original 2013 simulator. The other
direction, the champions of arms R, Rc and A in the MuJoCo engine, is transfer_scores.py.
Written on 27 November 2026, while arm D was running and before any score of it had been read.

usage, from the project folder:
    python paper/analysis/transfer_to_2013.py --arm D
        refuses while the arm has not been analysed (no report in paper/outcomes/)
    python paper/analysis/transfer_to_2013.py --rehearsal trialD_s --generation 3
        the same scoring for runs that are NOT an arm (trials): the champion of each complete
        run named <prefix><seed> with that many generations

What it does
  simulator    this campaign's build of the 2013 simulator, through the evaluation arm A's
               search used: the body written into the 2013 settings file where it is in the
               workspace, one simulation per champion, the score by the 2013 rule. The program
               is checked by its checksum against the one arms R, Rc and A ran with
  ratio        the score in the 2013 simulator over the score the run recorded in the MuJoCo
               engine: how much of its score a champion keeps
  statistics   how many champions and how many without a usable result; the scores in both
               simulators; the transfer ratio with a bootstrapped 95% interval of its median;
               Spearman's rank correlation between the two simulators' scores
  comparison   the transfer ratios against those of the 35 deposited no-cost champions under
               --preset cheney2013-floor (paper/outcomes/transfer_floor2013.json), which cross
               between the same two simulators in the other direction: A12 and two-sided
               Mann-Whitney U. Descriptive: no criterion, p not corrected

The report is printed and written to results/analysis/ as text, JSON and CSV.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))

import transfer_scores as ts                                  # noqa: E402  (sets one thread before numpy is loaded)
import numpy as np                                            # noqa: E402
import analyse_arm as aa                                      # noqa: E402
import protocol_stats as ps                                   # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402

REFERENCE_REPORT = 'transfer_floor2013.json'      # the deposited champions under the preset of arm D
REFERENCE_SET = 'deposit_noCost'
EARLIER_CHECKS = 'arm_A_checks.json'              # holds the checksum of the simulator arms R, Rc and A ran with


# --------------------------------------------------------------------------------------------
# the champions
# --------------------------------------------------------------------------------------------
def rehearsal_champions(prefix, generation, results=None):
    """The champion of every complete run <prefix><seed> of this project's search with that many
    generations: runs that are not an arm."""
    results = results or aa.SEARCH_RUNS
    seeds = sorted(int(d[len(prefix):]) for d in os.listdir(results)
                   if d.startswith(prefix) and d[len(prefix):].isdigit() and os.path.isdir(os.path.join(results, d)))
    out = []
    for seed in seeds:
        run = aa.load_search_run(os.path.join(results, f'{prefix}{seed}'), seed)
        if not aa.is_complete(run, generation):
            continue
        aa.load_search_champion(run)
        c = run['champion']
        index = int(re.search(r'individual (\d+)$', c['file']).group(1))
        grid = ts.grid_in_population(os.path.join(run['folder'], 'final_population.pkl'), index, c['original'])
        out.append({'set': f'rehearsal_{prefix}', 'label': f'seed {seed}', 'file': c['file'],
                    'evolved': float(c['original']), 'recorded_2013': None, 'grid': grid})
    return out


# --------------------------------------------------------------------------------------------
# the 2013 simulator
# --------------------------------------------------------------------------------------------
def simulator_of_arm_a(outcomes=None):
    """The checksums of the simulator and of the settings template that arm A's launcher recorded
    (and that are those of arms R and Rc), from the committed checks of arm A."""
    path = os.path.join(outcomes or aa.OUTCOMES, EARLIER_CHECKS)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        runs = json.load(f)['runs']
    return {'simulator_sha256': runs['simulator_sha256'], 'template_sha256': runs['template_sha256']}


def simulator_now():
    """The same two checksums of what is on this machine now."""
    import hashlib
    import start_arm
    from src.evolution.voxelyze2013_evaluator import TEMPLATE
    with open(TEMPLATE, 'rb') as f:
        template = hashlib.sha256(f.read()).hexdigest()
    return {'simulator_sha256': start_arm.programs()['sha256']['voxelize'], 'template_sha256': template}


def score_in_2013(champions, workers=10, evaluator=None):
    """Each champion once in the 2013 simulator, by the evaluation arm A's search used.
    -> one row per champion."""
    if evaluator is None:
        from src.evolution.voxelyze2013_evaluator import Voxelyze2013Evaluator
        evaluator = Voxelyze2013Evaluator(n_workers=max(1, workers))
    scores = [float(v) for v in evaluator.evaluate_batch([np.asarray(c['grid']) for c in champions])]
    rows = []
    for c, score in zip(champions, scores):
        if not c['evolved'] > 0:
            raise SystemExit(f"{c['label']}: a champion with a recorded score of {c['evolved']} has no transfer ratio.")
        grid = c13.workspace_grid(np.asarray(c['grid']))
        rows.append({'set': c['set'], 'label': c['label'], 'file': c['file'], 'voxels': int((grid != 0).sum()),
                     'lowest_layer': ts.lowest_layer(grid), 'evolved': float(c['evolved']), 'score': score,
                     'ratio': score / float(c['evolved']),
                     'no_result': bool(score == c13.MISSING_FITNESS), 'not_usable': bool(score == c13.FLOOR_FITNESS),
                     'blew_up': bool(score in (c13.MISSING_FITNESS, c13.FLOOR_FITNESS)), 'error': None})
    return rows


# --------------------------------------------------------------------------------------------
# the report
# --------------------------------------------------------------------------------------------
def reference_ratios(outcomes=None):
    """The transfer ratios of the deposited no-cost champions under the preset of arm D, as committed."""
    path = os.path.join(outcomes or aa.OUTCOMES, REFERENCE_REPORT)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        report = json.load(f)
    return [float(r['ratio']) for r in report['champions'] if r['set'] == REFERENCE_SET]


def build_report(rows, reference=None, n_boot=None, seed=None):
    report = {'champions': rows, 'set': ts.summarise(rows, n_boot, seed) if len(rows) >= 3 else None,
              'without_a_usable_result': {'no_result': int(sum(r['no_result'] for r in rows)),
                                          'not_usable': int(sum(r['not_usable'] for r in rows))}}
    if reference and len(reference) >= 3 and len(rows) >= 3:
        report['comparison'] = {'reference': f'{REFERENCE_SET} under --preset {ts.FLOOR_PRESET}', 'n_reference': len(reference),
                                'result': ps.compare([r['ratio'] for r in rows], reference, n_boot, seed, with_ratio=False)}
    return report


def render(report):
    L = [report['title'],
         f"Made {report['made']} with code {report['code']}; {report['settings']['n_boot']} bootstrap resamples, seed "
         f"{report['settings']['seed']}.",
         "Simulator: this campaign's build of the original 2013 simulator, through the evaluation of arm A's search; "
         'one simulation per champion.']
    sim = report.get('simulator')
    if sim:
        L.append(f"  Its checksum {sim['now']['simulator_sha256'][:12]} "
                 + ('is' if sim['same_simulator'] else 'IS NOT') + ' that of the program arms R, Rc and A ran with; '
                 + f"the settings template {sim['now']['template_sha256'][:12]} "
                 + ('is' if sim['same_template'] else 'IS NOT') + ' the one of arm A.')
    L.append('')
    for note in report.get('notes', []):
        L.append(f'NOTE: {note}')
    if report.get('notes'):
        L.append('')
    L.append('Scores in workspace widths. Transfer ratio: score in the 2013 simulator over the score the run recorded '
             'in the MuJoCo engine.')
    s = report['set']
    if s:
        w = report['without_a_usable_result']
        L += ['', f"{'set':<30}  {'n':>3}  {'no usable result':>16}  {'MuJoCo engine':>18}  {'2013 simulator':>18}  "
                  f"{'transfer ratio':>18}  {'95% of its median':>17}  {'rank correlation (95%)':>23}  {'ratio >= 1':>10}",
              f"{ts.set_title(report['champions'][0]['set']):<30}  {s['n']:>3}  {w['no_result'] + w['not_usable']:>16}  "
              f"{ts.q(s['evolved']):>18}  {ts.q(s['score']):>18}  {ts.q(s['ratio']):>18}  "
              f"{s['ratio_median_interval'][0]:>8.2f}-{s['ratio_median_interval'][1]:<8.2f}  "
              f"{s['rank_correlation']:>+6.2f} ({s['rank_correlation_interval'][0]:+.2f} to "
              f"{s['rank_correlation_interval'][1]:+.2f})  {s['kept_all_or_more']:>4} of {s['n']:<3}"]
    c = report.get('comparison')
    if c:
        r = c['result']
        L += ['', f"Against the transfer ratios of the {c['n_reference']} deposited no-cost champions under --preset "
                  f"{ts.FLOOR_PRESET}, which cross between the same two simulators in the other direction "
                  '(descriptive: no criterion, p not corrected):',
              f"  these champions {aa.med(r['arm_median'], r['arm_q25'], r['arm_q75'])}; the deposited champions "
              f"{aa.med(r['reference_median'], r['reference_q25'], r['reference_q75'])}; A12 {r['a12']:.2f} "
              f"({r['a12_interval'][0]:.2f}-{r['a12_interval'][1]:.2f}); p = {aa.pv(r['p'])}"]
    L += ['', 'PER CHAMPION',
          f"{'champion':<10}  {'voxels':>6}  {'lowest layer':>12}  {'MuJoCo':>7}  {'2013 sim':>8}  {'ratio':>6}  note"]
    for r in report['champions']:
        note = ('the simulator left no result' if r['no_result'] else
                'the result was not usable (the 2013 rule gives 0.0001)' if r['not_usable'] else '')
        L.append(f"{r['label']:<10}  {r['voxels']:>6}  {r['lowest_layer']:>12}  {r['evolved']:>7.3f}  {r['score']:>8.3f}  "
                 f"{r['ratio']:>6.2f}  {note}")
    return '\n'.join(L)


CSV_COLUMNS = ('set', 'label', 'file', 'voxels', 'lowest_layer', 'evolved', 'score', 'ratio', 'no_result', 'not_usable')


def write_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in rows:
            w.writerow([int(r[c]) if isinstance(r[c], bool) else r[c] for c in CSV_COLUMNS])


def finish(report, name, out_dir):
    report['made'] = datetime.datetime.now().isoformat(timespec='minutes')
    report['code'] = aa.code_version()
    report['settings'] = {'n_boot': ps.N_BOOT, 'seed': ps.SEED}
    text = render(report)
    print(text)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + '.txt'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1, default=float)
    write_csv(os.path.join(out_dir, name + '_champions.csv'), report['champions'])
    print(f"\nWritten to {os.path.join(out_dir, name)}.txt, .json and _champions.csv")


def main(argv=None, evaluator=None, simulator=simulator_now):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument('--arm', choices=['D'], help='the analysed arm whose champions are scored')
    what.add_argument('--rehearsal', metavar='PREFIX', help='runs that are not an arm: the start of their folder names')
    ap.add_argument('--generation', type=int, help='rehearsal only: the generations each run has')
    ap.add_argument('--workers', type=int, default=10, help='simulations side by side (default 10)')
    ap.add_argument('--results-dir', help=argparse.SUPPRESS)
    ap.add_argument('--out-dir', default=aa.OUT, help=argparse.SUPPRESS)
    ap.add_argument('--outcomes-dir', default=aa.OUTCOMES, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')

    notes = []
    if a.arm:
        champions = ts.arm_champions(a.arm, a.results_dir, a.outcomes_dir)
        if champions is None:
            print(f"Arm {a.arm} has not been analysed: there is no report of it in {a.outcomes_dir}.\n"
                  f"An arm's champions are scored only after the arm's own analysis (PROTOCOL.md, sections 9.4 and 9.7). "
                  f"Nothing was computed.")
            return 2
        title = (f"TRANSFER: the final champions of arm {a.arm}, evolved in this project's MuJoCo engine, scored in the "
                 f"original 2013 simulator.")
        name = f'transfer_arm_{a.arm}'
    else:
        if not a.generation:
            ap.error('--rehearsal needs --generation')
        champions = rehearsal_champions(a.rehearsal, a.generation, a.results_dir)
        if len(champions) < 3:
            print(f'Fewer than 3 complete runs named {a.rehearsal}<seed> have {a.generation} generations. '
                  f'Nothing was computed.')
            return 2
        title = (f"REHEARSAL, not an arm: the generation-{a.generation} champions of the runs {a.rehearsal}<seed>, "
                 f"scored in the original 2013 simulator.")
        name = f'transfer_to_2013_rehearsal_{a.rehearsal}{a.generation}'

    earlier, now = simulator_of_arm_a(a.outcomes_dir), simulator()
    reference = reference_ratios(a.outcomes_dir)
    if reference is None:
        notes.append(f'{REFERENCE_REPORT} is not in {a.outcomes_dir}, so the comparison with the deposited champions is '
                     f'not computed here.')
    report = build_report(score_in_2013(champions, a.workers, evaluator), reference)
    report['title'], report['notes'] = title, notes
    report['simulator'] = {'now': now, 'of_arm_A': earlier,
                           'same_simulator': bool(earlier and earlier['simulator_sha256'] == now['simulator_sha256']),
                           'same_template': bool(earlier and earlier['template_sha256'] == now['template_sha256'])}
    if not report['simulator']['same_simulator']:
        notes.append('The 2013 simulator on this machine is not, by its checksum, the program the earlier arms ran with.')
    finish(report, name, a.out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
