# The 2013 simulator as reference

21 November 2026. The original headless simulator of Cheney et al. 2013 (`Voxel_Sim_NoGui`), built unmodified from the authors' source archive and used as the measuring stick for this project's own engine.

## How it was built

`build_2013_simulator.sh`, run inside WSL Ubuntu 26.04 with g++ 15.2. No source file is edited; only compiler flags are set for the age of the code (C89 for the bundled zlib, C++98 with `-fpermissive` and three headers force-included). The archive's default Makefile targets the Intel compiler (`icpc -xhost -O3`), which the 2013 runs presumably used; this build uses the archive's own `MakefileG++` (`g++ -O3`). The prebuilt binary shipped in the archive is deleted, not run.

## 1. It reproduces its own recorded scores

`replay_in_2013_simulator.sh` runs every deposited generation-1000 robot file exactly as deposited (its own settings, 0.25 s) and `analyse_replay_2013.py` compares the result with the score in the file name. Raw output: `replay_2013_simulator.csv`.

| | Robots | Recorded median | Reproduced median | Median ratio | Within 1% | Within 5% | Within 20% | Rank agreement |
|---|---|---|---|---|---|---|---|---|
| No-cost, all robots | 1026 | 4.049 | 3.748 | 0.997 | 55% | 76% | 96% | +0.973 |
| No-cost, run champions | 35 | 4.393 | 4.320 | 0.988 | 43% | 66% | 97% | +0.881 |
| Actuated-cost, all robots | 1011 | 3.128 | 3.097 | 0.999 | 73% | 86% | 95% | +0.975 |
| Actuated-cost, run champions | 35 | 3.412 | 3.339 | 0.996 | 71% | 86% | 94% | +0.907 |
| Both conditions | 2037 | 3.232 | 3.222 | 0.998 | 64% | 81% | 95% | +0.984 |

- The simulator is deterministic: 151 groups of identical robots give identical results.
- 58 robots give no result. All 58 are recorded as failed (0.001) in 2013 as well.
- The typical robot is reproduced to a fraction of a percent, but about one in five differs by more than 5%. Same source, different compiler and thirteen years: the dynamics amplify small numerical differences. This is the floor for any reproduction of these numbers.
- One robot takes a median of 3.1 s on one core (10.6 s at most). The MuJoCo beam engine needs about 40 to 50 s for the same robots.

## 2. This project's robots in the 2013 simulator

`export_to_vxa.py` writes our robots as 2013 robot files, using a deposited file as the template so that every simulation setting is the original one. The writer reproduces all 35 deposited champions character for character, and re-exported deposited robots score exactly as the originals do. Raw output: `reverse_transplant.csv`.

| Robot | Score in our engine, as evolved | Score in the 2013 simulator |
|---|---|---|
| `cheney_score_s1` champion | 2.717 | 1.861 |
| `cheney_score_s1` final population, median of 30 | 0.903 | 0.883 |
| `cheney_score_s1` final population, best | 2.717 | 2.099 |
| `cheney_fix600_s1` champion | 2.612 (own-length score) | 1.823 |
| `cheney_corr_s1` champion (the soft-floor artefact) | 4.120 (own-length score) | 1.030 |

Across the 30 robots of the final population the two simulators rank them alike (rank agreement +0.89), and the median robot keeps 85% of its score. The fastest ones lose a quarter to a third.

For comparison, the deposited no-cost run champions score a median of 4.32 in the same simulator. So measured in one place, this project's best body is at about 45% of a typical 2013 champion. Those bodies were evolved under ±20% actuation, the volumetric law and ten times the damping, so this is a statement about that configuration, not yet about the search.

## 3. The engine against the reference

With the recorded scores now confirmed, the transplant test of 18 November (`../diagnostics_2026-11-18/`) measures a real difference between the two simulators: the deposited no-cost champions keep 0.34 of their score in the engine as it was configured, and 0.68 with the 2013 amplitude, Poisson and damping settings (0.77 for the actuated-cost champions). `check_option_matches_diagnostic.py` confirms that the engine's new `global_damping` option gives exactly the numbers that diagnostic measured.

Transfer is not symmetric. Bodies evolved under heavy damping move slowly and survive the move to the 2013 physics; bodies evolved under the 2013 physics rely on lightly damped dynamics that the heavier damping removes.

## 4. Evolving in the 2013 simulator

Since 21 November the evolution script can use the 2013 simulator as its evaluator:

```
python run_tendon_evolution.py --simulator voxelyze2013 --no-age-pareto --pop 30 --gen 1000 --seed 1 --name <new name>
```

- `src/evolution/voxelyze2013_evaluator.py` writes each body into the 2013 settings template, runs the simulator (inside WSL on Windows) and reads back the distance. It gives exactly the scores of the reference replay above, caches results by body (the simulator is deterministic, and the 2013 code cached the same way), and has the same interface as the MuJoCo evaluator.
- `src/evolution/voxelyze2013_template.vxa` is that template, produced by `make_template.py`. The 300 deposited robot files it was checked against are identical apart from the body and the name of the result file, in both conditions, so one template is the simulation settings of the whole experiment.
- `src/evolution/cheney2013.py` holds the rules read from the 2013 source: how a body is written, the score, what happens to missing, NaN and absurd results, the "fewer than 2 voxels is not simulated" rule, and the cost penalties. `--penalty actuated` reproduces the adjusted-to-original score ratio of the deposited cost-condition robots.
- With this simulator the physics options of the script are refused rather than ignored, because they could not take effect.

## 5. Re-running the original experiment itself

The archive also contains the search program that drove the 2013 runs (HyperNEAT v2.5 with the Softbots experiment). `build_2013_search.sh` builds it in WSL and `run_2013_search.sh` launches it the way the 2013 launch script did: a run folder with the two programs and the deposited settings file (`softbots2013Config`), then `./Hypercube_NEAT -I softbotTest.dat -O <name> -R <seed>`. It writes the same learning-curve file as the deposit. Each run uses one core, about 50 seconds per generation at the start.

Getting 2013 code to run on a 2026 system took four things, none of which changes what the program computes:

| What | Why |
|---|---|
| Compiler flags: C89 for the bundled zlib, C++14 with `-fpermissive` for the rest | The Boost that Ubuntu 26.04 ships (1.90) needs C++11 or later; the 2013 build used Boost 1.51 |
| `-D_GLIBCXX_USE_CXX11_ABI=0` | The program's own map class inserts by `memmove` on arrays holding `std::string`. That is valid only for the reference-counted string of the 2013 standard library. With today's string the keys are corrupted and settings are "not found". The switch selects the old string layout |
| `compat_2013_search.h`, force-included | The sources write `shared_ptr`, `mutex`, `thread`, `bind` unqualified after `using namespace boost` and `std`. In 2013 only Boost had those names. The header says, inside the program's namespaces, that the Boost ones are meant. It also includes `<iomanip>` early, because one source file includes it in the middle of a namespace |
| One patch, six lines of `main.cpp` (`patches_2013_search/`) | The same `shared_ptr` ambiguity at global scope, where the header cannot reach: the name is written `boost::shared_ptr` |

Two build-file adjustments as well: a `cmake_minimum_required` line prepended to two bundled CMake files, and absolute include paths. The authors' own build caches and binaries in the archive are deleted, not used. `-DBOOST_TIMER_ENABLE_DEPRECATED` re-enables two Boost headers the code includes.

`collect_2013_runs.sh` copies finished or running re-runs to `results/rerun2013/`, and `summarise_reruns.py` compares them with the deposited runs generation by generation. That is the quick view; the analysis fixed in the protocol is [`../analysis/analyse_arm.py`](../analysis/README.md).

**Pilot, 21 November: 12 seeds, 10 generations each** (`pilot10_P0_s1` to `s12`; a pilot, not part of any arm). Champion score, best so far:

| Generation | Re-run median (25th–75th percentile) | Deposited median (25th–75th percentile) | Ratio | A12 | p (Mann-Whitney) |
|---|---|---|---|---|---|
| 1 | 0.97 (0.81–1.27) | 0.85 (0.81–0.99) | 1.14 | 0.63 | 0.20 |
| 2 | 0.97 (0.93–1.39) | 0.96 (0.87–1.07) | 1.02 | 0.58 | 0.40 |
| 5 | 1.27 (1.02–1.53) | 1.25 (1.09–1.48) | 1.02 | 0.51 | 0.89 |
| 10 | 1.71 (1.34–2.10) | 1.50 (1.32–1.81) | 1.14 | 0.59 | 0.36 |

At generation 10 the ratio of medians is 1.14 with a bootstrapped 95% interval of 0.86 to 1.48 (0.86 to 1.50 until 22 November, when the summary still resampled the runs in folder-name order instead of seed order). Over these first ten generations the rebuilt original experiment is statistically indistinguishable from the deposited runs. Ten generations and twelve seeds cannot say more than that.

Cost: with 12 runs side by side, a generation took a median of 91 seconds (121 in the slowest run), so 1000 generations is at least 25 to 34 hours per run, and more once bodies grow.

## 6. Running an arm of the campaign

`start_arm.py` starts the 35 runs of arm R or Rc of [PROTOCOL.md](../PROTOCOL.md) and looks after them. From the project folder:

```
python paper\reference_2013\start_arm.py --arm R                        start it
python paper\reference_2013\start_arm.py --arm R --status               where every run is; starts nothing
python paper\reference_2013\start_arm.py --arm R --watch                follow its progress in this window
python paper\reference_2013\start_arm.py --arm R --stop                 stop its runs
python paper\reference_2013\start_arm.py --arm R --restart-incomplete   start it again after an interruption
```

- **The runs are looked after by a launcher without a window**, started through the Windows shell, so they depend neither on the program the command was typed in nor on any console window. The window that opens only shows the progress: closing it stops nothing, `--watch` opens the view again, and `--stop` is the way to stop the runs. Logging off, restarting Windows or shutting WSL down (`wsl --shutdown`) still ends them.
- **Why.** Until 23 November the launcher ran in the window and the window was the campaign. That morning both campaign windows were closed, and arm Rc lost 32 of its 35 runs nine hours in. Console windows are hosted by Windows Terminal here, where one click can close several.
- **It keeps Windows awake** for as long as it runs, with the keep-awake of `run_tendon_evolution.py`.
- **It starts the runs through `run_2013_search.sh`**, all 35 side by side, one core each. Finished runs are skipped, runs in progress are never touched, and a second launcher for the same arm is refused. If runs are alive without a launcher, starting the arm again adopts them instead of starting anything.
- **Every ten minutes** it copies the learning curves to `results/rerun2013/` and prints generations and time. It does not print scores.
- **At the end** it checks that every seed finished with 1000 generations and prints the comparison with the deposited runs. For each finished run `results/rerun2013/<run>/` then holds the learning curve, the robots of every recorded generation (the settings record the whole population every tenth generation), the genomes of the champions and of the final population as the program saved them, and the program's log.
- **Each launch is recorded** in `results/rerun2013/<arm>_launches.json`: time, command, code version, and the checksums of the two programs, their libraries and the settings file. A launch on a different build is refused. The protocol must be frozen before an arm starts.

**After an interruption** the unfinished runs cannot be continued. `--restart-incomplete` moves their folders to `runs/_interrupted/` on the WSL side and starts those seeds again from the beginning. That repeats the lost run instead of replacing it, because the program gives the same run for the same seed. Checked on 21 November:

| Check | Result |
|---|---|
| Seeds 1 to 3 for ten generations, three runs side by side (`det_P0_s1` to `s3`), against the same seeds in the pilot, twelve side by side | Every score identical in all ten generations |
| Seeds 1 and 2 cut short and started again, once by killing the launcher (`dryB`), once by Ctrl+C twice (`dryC`) | The same scores as the pilot, to the last digit |
| Both programs rebuilt from the scripts in this folder | Byte for byte the programs the pilot ran with (SHA-256 of the two programs and three libraries) |

Run alone, a run takes about 55 seconds per generation at the start. With all 35 side by side on this machine (i9-13900, 32 logical processors) every core is busy and the processor holds about half its peak clock speed, so a generation takes about 215 seconds (144 to 324 across the runs, first 20 minutes of arm R). That pace does not hold: later generations are much quicker. After 15 hours the median run of arm R was at generation 684, an average of 80 seconds per generation. The arm was complete after 22.2 hours (median run 20.1, fastest 15.4); the last runs speed up as the others finish.

`build_2013_simulator.sh` used to clear the whole reference folder, which also holds the run folders. It now replaces only the simulator's own folder, and both build scripts refuse to run while runs are in progress.

`--seeds`, `--gens` and `--tag` are for trials of the launcher. They need a tag of their own, so a trial cannot be written into an arm.

Arm R ran from 21 November 23:27 to 22 November 21:40. Its outcome is in [`../outcomes/README.md`](../outcomes/README.md).

The launcher without a window was tried on 23 November (`dryH_P0_s3`, `s5`): a close request to its progress window left launcher and runs alive; a second start was refused; `--stop` ended the runs and the launcher; the stopped seeds started again and gave the pilot's scores; and after the launcher alone was ended, starting again adopted the runs.

Arm Rc was started on 22 November at 23:19, on the same programs, libraries and settings file as arm R. It was cut short on 23 November at 08:46 (three runs had finished) and its 32 unfinished seeds were started again from the beginning at 09:00, with the launcher described above. The cost switch (`-P 2`) was tried first, on two seeds for ten generations (`dryRc_P2_s3`, `s5`): for all 50 simulated robots of the recorded generation the adjusted fitness is the original one times one minus actuated voxels over 1000, to seven digits. That is the rule read from the 2013 source, which the deposited cost robots follow as well. Under this switch the count in a robot's file name (`numFilled_`) is its number of actuated voxels, not of all voxels.

## Files

| File | Purpose |
|---|---|
| `build_2013_search.sh`, `compat_2013_search.h`, `patches_2013_search/` | Build the original search program |
| `start_arm.py` | Starts and looks after a whole arm of the campaign (section 6) |
| `run_2013_search.sh`, `collect_2013_runs.sh`, `stop_2013_runs.sh`, `summarise_reruns.py` | Re-run the original experiment, copy out and stop its runs, and compare it with the deposit |
| `make_template.py` | Writes the settings template from a deposited robot file, after checking the files agree |
| `build_2013_simulator.sh` | Builds the simulator in WSL from `research_reference/repositories/softbots2013Code.tgz` |
| `replay_in_2013_simulator.sh` | Runs a folder of robot files in it, in parallel, and writes a CSV |
| `analyse_replay_2013.py` | Table 1 above |
| `export_to_vxa.py` | Writes this project's robots as 2013 robot files |
| `check_option_matches_diagnostic.py` | Consistency check of the engine's damping option |
| `replay_2013_simulator.csv`, `reverse_transplant.csv` | Raw results |

The robot files themselves are in `research_reference/extracted/` (`dryad_gen1000/`, `reverse_transplant_vxa/`), which is kept out of git.
