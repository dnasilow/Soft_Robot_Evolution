"""Make the settings template the 2013-simulator evaluator fills with a body.

Takes one deposited 2013 robot file, blanks its ten <Layer> rows and gives the result file a fixed
name (fitness.xml). Before writing, it checks that the deposited files really are identical apart
from those two things, in both the no-cost and the actuated-cost condition, so that one template
stands for the simulation settings of the whole experiment.

usage:  python paper/reference_2013/make_template.py
writes: src/evolution/voxelyze2013_template.vxa
"""
import glob
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DRYAD = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')
OUT = os.path.join(ROOT, 'src', 'evolution', 'voxelyze2013_template.vxa')
LAYER = re.compile(r'(<Layer><!\[CDATA\[)(.*?)(\]\]></Layer>)', re.S)
FITFILE = re.compile(r'(<FitnessFileNm>)(.*?)(</FitnessFileNm>)', re.S)


def normalise(text):
    text = text.replace('\r\n', '\n')
    text = LAYER.sub(lambda m: m.group(1) + '0' * 100 + m.group(3), text)
    return FITFILE.sub(lambda m: m.group(1) + 'fitness.xml' + m.group(3), text)


def main():
    files = []
    for cond in ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated'):
        files += sorted(glob.glob(os.path.join(DRYAD, cond, 'run_*', 'Gen_1000', '*.vxa')))[::7]
    texts = {normalise(open(f, encoding='iso-8859-1').read()) for f in files}
    print(f'{len(files)} deposited files checked, {len(texts)} distinct after blanking body and result-file name')
    if len(texts) != 1:
        raise SystemExit('the deposited files do not share one set of settings - not writing a template')
    text = texts.pop()
    if len(LAYER.findall(text)) != 10 or len(FITFILE.findall(text)) != 1:
        raise SystemExit('unexpected file structure')
    with open(OUT, 'w', encoding='iso-8859-1', newline='\n') as fh:
        fh.write(text)
    print(f'wrote {OUT} ({len(text)} characters)')
    for tag in ('DtFrac', 'BondDampingZ', 'ColDampingZ', 'SlowDampingZ', 'SelfColEnabled', 'ColSystem',
                'CollisionHorizon', 'PoissonKickBackEnabled', 'StopConditionType', 'StopConditionValue',
                'GravAcc', 'TempAmp', 'TempBase', 'TempPeriod', 'Lattice_Dim', 'X_Voxels', 'Y_Voxels', 'Z_Voxels'):
        m = re.search(rf'<{tag}>([^<]*)</{tag}>', text)
        print(f'  {tag:<24}{m.group(1) if m else "(absent)"}')


if __name__ == '__main__':
    main()
