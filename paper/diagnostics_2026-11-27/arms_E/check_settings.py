"""Do the options of arms E1 to E3 give the settings the protocol names, and nothing else?
(PROTOCOL.md, section 9.8, point 1.)

For arm D and for each of the three arms a run of the search's own command line is made with the
arm's engine options as the launcher has them (search_arm.ARMS), small enough to take a minute or
two: workspace 5, population 4, two generations, one robot at a time, seed 101. That is the seed
of no arm: arm D has seeds 1 to 10 and arms E1 to E3 have seeds 1 to 3, and no run of an arm's
seed is made before the arm is started. What each run recorded of itself (manifest.json) is then
set against the run with arm D's options: which settings differ, and which entries of the preset
were not applied. Each arm must differ from arm D in the one setting it undoes:

    E1   damping_global                 0.001 -> 0.01
    E2   amp, poisson                   0.14 -> 0.2, off -> on
    E3   preset, floor_contact, start   cheney2013-floor -> cheney2013, rule2013 -> voxelyze,
                                        workspace -> floor

usage, from the project folder:
    python paper/diagnostics_2026-11-27/arms_E/check_settings.py
Runs that are complete already are not made again; they are kept in
results/diagnostics_2026-11-27/arms_E/. Written next to this file: settings.json.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))
import search_arm                                                 # noqa: E402

WORK = os.path.join(ROOT, 'results', 'diagnostics_2026-11-27', 'arms_E')
SEED = 101
SMALL = ['--pop', '4', '--grid-size', '5']        # in place of the arm's --pop 30 and the preset's workspace of 10
EXPECTED = {'E1': {'damping_global'}, 'E2': {'amp', 'poisson'}, 'E3': {'preset', 'floor_contact', 'start'}}
NOT_SETTINGS = ('name',)                          # what differs between any two runs


def options_of(arm):
    """The arm's command as the launcher has it, with the small population and workspace."""
    words = list(search_arm.ARMS[arm]['runner'])
    return words[:words.index('--pop')] + SMALL


def record_of(arm):
    """Make the small run (unless it is there) and return the last start it recorded of itself."""
    run = f'settings{arm}_s{SEED}'
    manifest = os.path.join(WORK, 'results', run, 'manifest.json')
    done = os.path.join(WORK, 'results', run, 'final_population.pkl')
    if not os.path.isfile(done):
        os.makedirs(WORK, exist_ok=True)
        command = [sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py')] + options_of(arm) + [
            '--gen', '2', '--workers', '1', '--seed', str(SEED), '--name', run]
        r = subprocess.run(command, cwd=WORK, env=search_arm.run_environment(), capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            raise SystemExit(f'The run with the options of arm {arm} ended with code {r.returncode}:\n'
                             + r.stdout[-1500:] + r.stderr[-1500:])
    with open(manifest, encoding='utf-8') as f:
        return json.load(f)['invocations'][-1]


def main():
    base = record_of('D')
    out = {'seed': SEED, 'small': SMALL, 'arm_D': {'options': options_of('D'), 'preset_applied': base['preset_applied']},
           'arms': {}}
    good = True
    for arm in ('E1', 'E2', 'E3'):
        mine = record_of(arm)
        differ = {k: [base['settings'].get(k), v] for k, v in mine['settings'].items()
                  if k not in NOT_SETTINGS and v != base['settings'].get(k)}
        differ.update({k: [v, None] for k, v in base['settings'].items() if k not in mine['settings']})
        not_applied = sorted(k for k in base['preset_applied'] if k not in mine['preset_applied'])
        applied_otherwise = {k: [base['preset_applied'][k], v] for k, v in mine['preset_applied'].items()
                             if k in base['preset_applied'] and base['preset_applied'][k] != v}
        as_named = set(differ) == EXPECTED[arm] and mine['threads'] == search_arm.ONE_THREAD
        good = good and as_named
        out['arms'][arm] = {'options': options_of(arm), 'settings_that_differ_from_arm_D': differ,
                            'preset_entries_not_applied': not_applied,
                            'preset_entries_applied_with_another_value': applied_otherwise,
                            'differs_in_the_named_setting_and_no_other': bool(as_named)}
        print(f"arm {arm}: {' '.join(options_of(arm)[:-len(SMALL)])}")
        for k, (was, now) in sorted(differ.items()):
            print(f'    {k}: {was!r} under arm D, {now!r} here')
        print(f"    entries of arm D's preset not applied here: {not_applied or 'none'}"
              + (f'; applied with another value: {applied_otherwise}' if applied_otherwise else ''))
        print(f"    differs from arm D in the setting the protocol names and in no other: {'yes' if as_named else 'NO'}")
    out['each_arm_differs_in_its_one_setting_only'] = bool(good)
    with open(os.path.join(HERE, 'settings.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    print('\nEach arm differs from arm D in its one setting only.' if good else '\nA SETTING IS NOT AS NAMED: see above.')
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
