# Literature notes 6 — Citing-works sweep for Cheney et al. 2013 (OpenAlex and Scite)

Date: 24 November 2026. Scope: test the conclusion of [LITERATURE.md](../LITERATURE.md), section 2 ("no independent re-implementation with a comparison against the 2013 numbers was found, and no re-analysis of the deposited data") with two sources the earlier survey did not have: the OpenAlex connector (complete citing lists, full-text and semantic search) and the Scite connector (citation statements).

Companion file: [cheney2013_citing_works.csv](cheney2013_citing_works.csv), one row per citing work (477 rows).

## 0. How to read these notes

Every claim carries one tag saying how it was checked in this sweep:

- `[full text]` body text read through Scite (whole text or term-matched excerpts).
- `[abstract]` abstract read in OpenAlex or Scite (OpenAlex list views cut abstracts short; where only the cut version was read this is said).
- `[citation statement]` the sentence in the citing paper that carries the citation, as returned by Scite.
- `[title only]` nothing but the bibliographic record was seen.
- `[tool output]` a count or a list returned by a tool (no paper text involved).
- `[earlier survey]` not re-checked here; taken from notes 1 to 5, which give their own verification level.

Paper text is paraphrased throughout, not quoted. "Not found" means not found with these tools, not proven absent.

## 1. Method

### 1.1 Tools

- OpenAlex connector: `get_work`, `list_citations` (direction citing and references), `search_works` (keyword search over title, abstract and keywords; full-text search; semantic search).
- Scite connector: `get_citation_statements`, `search_literature`, `read_fulltext`. Read-only calls only.
- Outside the two connectors, four page fetches were tried for the abstracts of the two closest unread candidates (section 1.6).

### 1.2 Versions of the paper in OpenAlex `[tool output]`

| Record | What | DOI | Counter on the record | Citing works that can be listed |
|---|---|---|---|---|
| W2120652436 | GECCO 2013, pp. 167-174 | 10.1145/2463372.2463404 | 287 | 278, plus 1 marked as pulled |
| W2610992585 | ACM SIGEVOlution 7(1), 2014, pp. 11-23 | 10.1145/2661735.2661737 | 220 | 215 |
| W6948351743 | Dryad dataset (2014) | 10.5061/dryad.m3s84 | 0 | 0 |

- A title search for the phrase "Unshackling evolution" returns only the two paper records. No preprint or third version is held.
- 17 works are linked to both paper records, 261 only to the GECCO record, 198 only to the SIGEVOlution record: **476 distinct citing works**, 477 with the pulled one (an arXiv copy of a paper that is in the list anyway).
- The counters on the records (287 and 220) are higher than the lists (279 and 215). The 13 extra items could not be listed with any filter tried.
- The earlier survey read the Semantic Scholar list (376 records on 18 November) and knew only the OpenAlex count for the GECCO record (279). The 198 works linked only to the SIGEVOlution record are the main new material; 170 of them are from 2021 or later. How many of the 476 were already in the Semantic Scholar list could not be established: that list is not among the survey files read for this sweep.

### 1.3 The CSV

- Columns: `openalex_id, doi, title, year, venue, type, cited_by_count, cites_version, screen, screen_basis, screen_note`. UTF-8, no byte-order mark. Sorted by year (newest first), then title.
- `cites_version`: `GECCO2013`, `SIGEVO2014` or `both`.
- `screen`: `a` reproduction, replication, re-run or re-implementation of the 2013 experiment, or use of its deposited data or code; `b` quantitative comparison against the 2013 method on the same task; `c` morphology outcome or what changes it; `d` simulator or benchmark positioned against VoxCad/Voxelyze; `e` reproducibility or replication study in evolutionary robotics or artificial life; `-` none of these. A question mark means the code rests on a title or an abstract that does not settle it.
- `screen_basis`: `title only`, `abstract`, `citation statement`, `full text`, or `earlier survey`.
- The rows were typed from the tool output page by page (10 pages of up to 50), then checked by script: 8 fields per row, no duplicate identifier, 278 + 198 = 476 rows as the tool reported. A typing slip in a single title or count is still possible. Three venue strings were shortened (ICRA, NeurIPS, ECAL 2015), and book chapters titled "Introduction" carry their book title in square brackets. `cited_by_count` is OpenAlex's value on 24 November 2026.
- Composition `[tool output]`: 189 conference papers, 171 articles, 48 preprints, 33 dissertations, 15 book chapters, 13 reviews, 3 peer-review records, 5 others. 26 rows have no DOI. By year: 7 (2013), 26, 28, 17, 32, 25, 43, 34, 43, 42, 46, 44, 39, 51 (2026).

### 1.4 Screening (task 2)

- All 477 rows were screened on the title.
- 102 rows carry a code other than `-`: 1 `a?`, 7 `b`, 11 `b?`, 55 `c` or `c?` (two of them also `b`, one also `d`), 30 `d` or `d?`, 1 `e?`.
- Basis of the 477 screening decisions: 399 title only; 45 earlier survey; 18 abstract; 13 citation statement; 2 full text.
- No row earned an unqualified `a`, and no row is a replication study in the sense of `e`.

### 1.5 Scite citation statements (task 3) `[tool output]`

| | GECCO DOI | SIGEVOlution DOI | Dryad DOI |
|---|---|---|---|
| Citing publications known to Scite | 239 | 176 | only the paper itself |
| Citation statements with text | 82 | 73 | 0 |
| ... classed supporting | 0 | 0 | 0 |
| ... classed contrasting | 0 | 0 | 0 |
| ... classed mentioning | 80 | 71 | 0 |
| ... unclassified | 2 | 2 | 0 |
| Distinct citing papers behind the statements | 47 | 52 | 0 |
| Snippet withheld by the publisher's licence | 26 | 17 | - |

Term filter, one term at a time (number of statements returned):

| Term | GECCO DOI | SIGEVOlution DOI |
|---|---|---|
| reproduc | 1 | 2 |
| replicat | 0 | 0 |
| re-implement | 0 | 0 |
| reimplement | 0 | 1 |
| "same setup" | 0 | 0 |
| "same parameters" | 0 | 0 |
| re-run | 0 | 0 |
| unable | 2 | 4 |
| "could not" | 0 | 0 |
| differ | 35 | 27 |
| validate | 2 | 7 |
| dataset | 9 | 1 |
| Dryad | 0 | 0 |
| also tried: replicate, replication, reproduction, reproducibility | 0 each | 0 each |

- What the hits are:
  - "reproduc", GECCO DOI: one statement in Lipson, "Challenges and opportunities for design, simulation, and fabrication of soft robots", Soft Robotics 2013, DOI 10.1089/soro.2013.0007, section "potential approaches". Snippet withheld. Same year and a co-author of the 2013 paper, so not a reproduction. `[citation statement, text not shown]`
  - "reproduc", SIGEVOlution DOI: two statements in a Spanish-language overview, "Vida artificial y criaturas virtuales", 2022, DOI 10.32870/recibe.v11i2.253. Snippets withheld. `[citation statement, text not shown]`
  - "reimplement", SIGEVOlution DOI: Sun & Lueth 2026 (review), which calls voxcraft-sim a GPU re-implementation of Voxelyze. `[citation statement]`
- The Scite term filter is not a literal match on the snippet. Of the 9 statements returned for "dataset", none of the visible ones contains the word; the filter seems to match elsewhere in the citing paper. A literal search of the 112 visible snippets gave: reproduc 0, replicat 0, re-implement 0, reimplement 1, same setup 0, same parameters 0, re-run or rerun 0, unable 2, could not 0, differ 17, validat 0, dataset 0, Dryad 0. `[tool output]`
- The CSV does not repeat the 155 statements. Those that matter are in sections 3 and 4.

### 1.6 What could not be reached

- **Abstract and text of Gu et al. 2019 and Ogawa 2019** (the two citing works whose titles come closest to a re-run). OpenAlex and Scite hold no abstract; Scite reports no readable text. The publisher pages redirected to an authorisation service and were not followed. The Semantic Scholar record of Gu et al. has no abstract, only a machine-generated one-line summary; the record of Ogawa 2019 returned "not found".
- **43 of 155 Scite snippets** are withheld. Among them: five statements in Cheney et al. 2018 (J. R. Soc. Interface), three in Lipson 2013, one in Hiller & Lipson 2014 (discussion section), three in Mertan & Cheney 2023, one each in Kriegman et al. 2019 and Eguiarte-Morett & Aguilar 2023.
- **Most ACM-published citing papers have no statement text in Scite**, only a bare link (for example Methenitis et al. 2015 and Gravina et al. 2017). The list of such bare links could not be paged past its first 100 entries.
- **Scite's stance labels are of little use here.** The tool's own description says that its supporting and contrasting labels are conservative and that most statements end up as mentioning. Zero of each is therefore weak evidence either way.
- **Full text** was readable for two candidates only (Haile et al. 2022; Sui et al. 2019). La Cava & Moore 2018, Kimura et al. 2016 and 2021 and Marzougui et al. 2022 were read as abstracts.
- **Google Scholar** was not queried. It normally lists more citing items than either index (theses, reports, items without DOI). Its count was not checked.
- **Each index misses works the other has.** Among the 142 citing papers on Scite's first result page for each DOI, 8 are in neither OpenAlex list (none relevant by title). OpenAlex's reference lists for Kriegman et al. 2018 (Sci. Rep.) and Kriegman et al. 2020 (PNAS) contain no entry for the 2013 paper, so those two are absent from the CSV; whether the papers cite it was not checked in their text. `[tool output]`
- OpenAlex keyword search rejects wildcards in its default (stemmed) mode. Word forms were written out instead.

## 2. Has anyone reproduced or re-analysed Cheney et al. 2013?

**Answer: no reproduction, replication, re-implementation or re-analysis was found.** The earlier conclusion stands, now on a wider base.

Evidence:

1. **Citing works.** None of the 477 works that OpenAlex links to either version of the paper presents itself, in its title or (where read) its abstract, as a reproduction or replication of the 2013 experiment. `[title only]` for 399, better for the rest (section 1.4).
2. **Citation statements.** In 155 statements from 98 citing papers (112 of the statements with visible text), no visible snippet contains a word built on reproduc-, replicat-, re-run, re-implement- or validat-, nor "same setup", "same parameters", "could not", "dataset" or "Dryad". The three hits of the server-side filter are explained in section 1.5. `[citation statement]`
3. **The deposit.** The Dryad record has no citing work in OpenAlex and none in Scite apart from the paper itself. A full-text search of OpenAlex for the dataset DOI suffix and for the archive and repository names (`softbots2013`, `softbots2013Code`, `softbotEvolution`) returns nothing. `[tool output]`
4. **Independent searches** (section 6) for reproduction work that does not cite the paper found none.
5. **What does exist** is re-use of the task as a baseline inside studies that ask a different question (section 3). None of those read in full reports its baseline next to the 2013 numbers; for those seen only as abstracts this is not known. `[abstract]`, `[full text]` and `[earlier survey]` as marked in the table.

How sure: fairly sure that no reproduction study is indexed in OpenAlex, Scite or Semantic Scholar. Less sure that none exists at all. The limits:

- 399 of 477 works were judged on the title. A re-run reported inside a paper on another subject, or in one of the 33 dissertations, would not show.
- One candidate could not be read (Gu et al. 2019, section 3).
- Full-text search in OpenAlex covers only part of the corpus, and its phrase matching is stemmed, not exact.
- Google Scholar, course reports, blog posts and code repositories are outside these indexes. The two student term papers and the hobby ports in note 1, section 6, are of that kind; they did not appear in any result of either connector.
- A reproduction that does not cite the paper and uses none of the search words would be missed.

## 3. Closest works of kinds (a) and (b)

"Same task" means: voxel bodies of the 2013 materials, CPPN encoding, locomotion distance as fitness, Voxelyze-family physics.

| Work | Kind | What it did, exactly | Reports its numbers against the 2013 results? | Checked |
|---|---|---|---|---|
| Gu, Zhang, Wu, Li, Zhang, Gao, Luo 2019, "Research on motion evolution of soft robot based on VoxCAD", ICIRA 2019, LNCS, DOI 10.1007/978-3-030-27535-8_3. Cites the SIGEVOlution version. | a? | An independent group evolving soft-robot motion in VoxCAD. A machine-generated summary says a CPPN is used and a four-legged walker is analysed as a check of the method. Nothing seen says it repeats the 2013 runs. | Unknown | `[title only]` plus a machine summary |
| Methenitis, Hennes, Izzo, Visser 2015, GECCO, DOI 10.1145/2739480.2754731 | b | Same simulator and materials; CPPN-NEAT with the 2013 parameters as fitness-search baseline against novelty search; 10 runs; lattices 5^3 to 10^3; four gravity levels. | No | `[earlier survey]`, full text |
| Mouret & Clune 2015, arXiv:1504.04909 | b | Same domain at 10^3; MAP-Elites against two evolutionary algorithms without speciation; 5 to 8 finished runs. One of the authors is an author of the 2013 paper. | No | `[earlier survey]`, full text |
| Gravina, Liapis, Yannakakis 2017, GECCO Companion, DOI 10.1145/3067695.3076072 | b | Objective search against novelty and surprise search at 5^3; 30 runs. | No | `[earlier survey]`, full text |
| Gravina, Liapis, Yannakakis 2018, GECCO, DOI 10.1145/3205455.3205503 | b | The same at eight lattice sizes, 90 runs per condition, original simulator with the settings of Methenitis et al. The largest independent re-run of the task. | No | `[earlier survey]`, full text |
| Gravina, Liapis, Yannakakis 2019, GECCO Companion, DOI 10.1145/3319619.3321987 | b | MAP-Elites with biased parent selection at 5^3. Not among the citing works: its reference list in OpenAlex (10 entries) has no entry for the 2013 paper. | No | `[earlier survey]`; reference list `[tool output]` |
| La Cava & Moore 2018, ALIFE, DOI 10.1162/isal_a_00044 | b | Lexicase selection, objectives found by clustering, and novelty search against age-fitness Pareto optimisation and random search, on soft robots scored by distance. Reports that random search with elitism was competitive with published methods. The simulator is not named in the abstract. | Not in the abstract | `[abstract]` |
| Haile, Barber, Chen 2022, "Transitional pattern producing networks for faster evolution of soft robots", TechRxiv preprint, DOI 10.36227/techrxiv.20436018.v1. Cites the SIGEVOlution version. | b | Four material types and simulator settings taken from an earlier study (its reference [9]; the reference list is not in the text that could be read, but the description of the materials matches the 2013 paper). A new encoding against CPPN, neural cellular automata and a sinusoidal network, each evolved with a (1+1) evolution strategy from 30 random starts, at 5^3; examples at 10^3. No CPPN-NEAT run as in 2013. The CPPN arm did worst, which the authors put down to the tiny population. They note that weak designs score by falling over or circling. | No | `[full text]` |
| Singh 2025, CSITSS, DOI 10.1109/csitss67709.2025.11295732 | b | CPPN-NEAT with novelty search under three gravity levels, against a direct encoding. | No, as far as the abstract shows | `[earlier survey]`, abstract; no full text in Scite |
| Kimura, Jin, Niiyama, Kuniyoshi 2016, IEEE/SICE SII, DOI 10.1109/sii.2016.7844033 | b? | Combines CPPN-NEAT networks evolved for single tasks into multi-task soft robots; two locomotion tasks; compared with an existing multi-task method. Simulator not named in the abstract. | Not in the abstract | `[abstract]` |
| Kimura, Niiyama, Kuniyoshi 2021, RoboSoft, DOI 10.1109/robosoft51838.2021.9479428 | b? | The same idea with a modular combination of genotype networks; land and water locomotion of voxel creatures; some designs built. | Not in the abstract | `[abstract]` |
| Marzougui, Biondina, wyffels 2022, GECCO Companion, DOI 10.1145/3520304.3528977 | b? | One shared genome against separate genomes for body and control, plus two extreme variants, on a soft-robot locomotion task; the shared genome did better. Simulator not named. | Not in the abstract | `[abstract]` |
| Ogawa 2019, BICT 2019, DOI 10.1007/978-3-030-24202-2_9 | b? | Multi-objective evolution of soft robots in different environments. | Unknown | `[title only]` |

Not independent, listed for completeness `[earlier survey]`: the authors' own follow-ups (Cheney et al. 2014, 2015, 2016, 2018) and the same lineage (Corucci et al. 2016, 2018; Kriegman et al. 2017 onward). Biazzi et al. (bioRxiv 2022, eLife reviewed preprint) use Voxelyze in a different regime and are kind (c).

Reading: the 2013 configuration (its simulator, materials and CPPN-NEAT) has been re-run as a baseline in at least four studies by three groups outside the original one: Methenitis et al. 2015 (10 runs), Gravina et al. 2017 (30) and 2018 (90), and Singh 2025 (number of runs not seen). Others re-used the task with a different search method or encoding. Each time the question was whether something else beats the baseline. None of the papers read in full (here or in the earlier survey) sets its baseline next to the published 2013 values, checks the simulator settings against the deposit, or looks at the deposited runs. For the papers seen only as abstracts or titles this is open (section 7).

## 4. Citation statements worth keeping

All `[citation statement]`, paraphrased; section names as given by Scite.

- **Corucci et al. 2018**, Soft Robotics, DOI 10.1089/soro.2017.0055, discussion: four-legged bodies with clear walking gaits evolved in their setup and had not been seen in the earlier studies that used very similar tools (the 2013 paper is among the four cited). They offer four possible reasons: a wider stiffness range, separate networks for body and control, their objectives, and better parameter tuning. Already in note 1 from the full text; the statement confirms the wording.
- **Lai, Fol Leymarie, Latham, Arita, Suzuki 2021**, "Virtual creature morphology - a review", Computer Graphics Forum, DOI 10.1111/cgf.142661, section on amorphous robots: as far as the reviewers could establish, the public VoxCAD repository appeared after the 2013 paper and was first described in 2014, so the 2013 authors probably worked from an earlier copy. The same review restates the penalty-function result: the four cost functions steer morphology without changing overall performance.
- **Shen et al. 2026 (EvoGymCM)**, arXiv:2604.08258, related work: early voxel work relied on custom physics engines, which stood in the way of standardised comparison between methods.
- **Sun & Lueth 2026**, Biomimetics, DOI 10.3390/biomimetics11100714 (review): presents Voxelyze as the de facto standard simulator for evolved soft robots, evosoro as a Python wrapper around it, and voxcraft-sim as a GPU re-implementation.
- **Stroppa et al. 2024**, Robotica, DOI 10.1017/s0263574724001152 (survey), section on the importance of stating the optimisation method: several soft-robot design papers do not say which evolutionary algorithm they used; for one VoxCAD study the surveyors had to work it out from the software's built-in genetic-algorithm add-on.
- **Hockings & Howard 2020**, Frontiers in Bioengineering and Biotechnology, DOI 10.3389/fbioe.2020.00621 (review): credits Cheney and co-authors with developing the simulator. An example of the loose way secondary sources describe the system; the simulator is Hiller and Lipson's.
- **Tsompanas & Balaz 2024**, Frontiers in Robotics and AI, DOI 10.3389/frobt.2024.1337722, introduction: restates the 2013 direct-encoding result (champions barely better than random initial bodies) as the reason for choosing CPPNs.
- **Kobayashi et al. 2024**, Science Advances, DOI 10.1126/sciadv.adn6129, results: sets the cost of its gradient-based optimisation (under two thousand forward simulations) against the cost of evolutionary methods, citing the 2013 paper among them.
- **"Diversity-based topology optimization of soft robotic grippers"**, Advanced Intelligent Systems 2024, DOI 10.1002/aisy.202300505 (known to Scite, not in the OpenAlex lists; authors not shown in the record read): designs from this family of simulators either cannot be manufactured or do not survive the move to hardware.

## 5. Relevant works the existing survey does not cover

Checked against LITERATURE.md and notes 1 to 5 by name search. Ordered by use to a reproduction paper.

1. **Haile, Barber, Chen 2022** (section 3). An independent team took material types and simulator settings from the earlier work and ran 30 starts per encoding, without checking against the original values. The clearest recent case of "re-used, never reproduced". Its remark on designs that score by falling or circling supports an audit of what the distance measure rewards. `[full text]`
2. **Kimura et al. 2016 and 2021** (section 3). A second independent line on CPPN-NEAT voxel robots, cited by Biazzi et al. next to the 2013 paper as a standard use of CPPNs. Simulator and settings need the full text. `[abstract]`; the Biazzi mention is a `[citation statement]`
3. **Gu et al. 2019** (section 3). The one title that names the simulator and the encoding together. Unread. `[title only]`
4. **La Cava & Moore 2018** (section 3). Note 1 listed it with content unverified. The abstract's finding that random search with elitism matches published methods bears on how strong the 2013 baseline is. `[abstract]`
5. **Marzougui et al. 2022** (section 3). Encoding design for body and control on a soft-robot locomotion task. `[abstract]`
6. **Lai et al. 2021** (section 4). A review that noticed the provenance question of the simulator code. Useful for the paragraph on why the deposited code, not the public repository, is the reference. `[citation statement]`
7. **Sui, Cai, Bie, Zhang, Zhao and one more author 2019**, "Automatic generation of locomotion patterns for soft modular reconfigurable robots", Applied Sciences, DOI 10.3390/app10010294. An independent group optimised gaits of a pneumatic modular soft robot in VoxCAD and built it. They call the VoxCAD model inaccurate but efficient and conclude that it was able to simulate their real robot. One more data point on simulator fidelity next to Kriegman et al. 2020 (note 4). `[full text]`, term-matched excerpts
8. **Stroppa et al. 2024** and **Sun & Lueth 2026** (section 4). Two recent surveys of soft-robot design optimisation. The first documents under-reported methods; the second shows that Voxelyze is still described as the standard in late 2026. `[citation statement]`
9. **Shen et al. 2026 (EvoGymCM)**. Already in notes 1, 2 and 4, but its statement that custom engines blocked standardised comparison is new and quotable in substance. `[citation statement]`
10. **Cochevelou, Bonner, Schmidt 2023**, "Differentiable soft-robot generation", GECCO 2023, DOI 10.1145/3583131.3590408. The reference that note 3 could not locate. Material-point-method co-optimisation of shape and muscle actuation of 3D soft robots in three scenarios, of which walking and walking up stairs were visible. `[abstract]`, cut version
11. **Collins, Chand, Vanderkop, Howard 2021**, "A review of physics simulators for robotic applications", IEEE Access, DOI 10.1109/access.2021.3068769 (388 citations in OpenAlex), and **Collins 2022**, a thesis on the reality gap, DOI 10.5204/thesis.eprints.230537. General background for the simulator-choice section. `[abstract]`, cut version; thesis `[title only]`
12. **Tsompanas, Alcaraz-Herrera, Balaz, Adamatzky 2024 to 2026**, six papers on CPPN-NEAT and HyperNEAT design of soft and biohybrid actuators (DOIs 10.3389/frobt.2024.1337722, 10.1016/j.birob.2024.100205, 10.1002/cpe.70204, 10.1007/978-3-031-56855-8_17, 10.5220/0012919300003837, 10.1007/978-3-032-15635-8_8). A current independent user group of the 2013 method for a different target (bending actuators, not locomotion). One of them compares neuroevolution with age-fitness Pareto optimisation. Simulator not confirmed. `[abstract]` or `[citation statement]`, as marked in the CSV
13. **Ogawa 2019** (section 3) and **Ogawa, Nakamura, Naruse 2018**, DOI 10.1299/jsmermd.2018.1a1-d15, which classifies the motion of voxel-model soft bodies with a one-dimensional cellular automaton. `[title only]` and `[abstract]`, cut version
14. **Collins, Cottier, Howard 2019**, CEC, DOI 10.1109/cec.2019.8790166. Direct (spline) against CPPN-NEAT representation for 3D-printed hexapod legs on a voxel grid. A test of the "generative beats direct" claim on another problem. `[abstract]`, cut version
15. **Roper, Katsaros, Fernando 2014**, "Voxel Robot: a pneumatic robot with deformable morphology", SAB 2014, DOI 10.1007/978-3-319-08864-8_22. An early physical voxel robot that cites the 2013 paper. `[title only]`
16. **Pandey & Windridge 2020**, DOI 10.1007/978-3-030-51992-6_12. Genetic training of deep networks, tested on a system the abstract likens to an electrophysiological soft robot. Whether it runs the authors' 2014 code is not stated. `[abstract]`
17. **Three eLife review records** for Biazzi et al. (DOIs 10.7554/elife.87180.1.sa0, .2.sa1, .2.sa2) are themselves linked as citing the 2013 paper. Public reviews of the closest study in the same simulator; not read. `[title only]`
18. **Works on the topic that are not linked as citing** (found through OpenAlex's related-works field and the searches): Ashwin et al. 2025, GECCO Companion, DOI 10.1145/3712255.3734326 (multi-task evolution of voxel soft robots); Sabarish & Velayutham 2026, DOI 10.1007/978-3-032-18480-1_13; Dogaru, El Saliby, Medvet 2025, DOI 10.1109/mind67540.2025.11351733 (pleiotropy in body-brain evolution); Ghosh and a co-author 2021, a two-fingered gripper simulated in VoxCAD, DOI 10.1109/icccnt51525.2021.9580168. None looks like a reproduction. `[title only]`

Two small updates to the earlier notes `[tool output]`:

- Note 4 gave the SIGEVOlution reprint from a search snippet. OpenAlex confirms volume 7, issue 1, pages 11-23, DOI 10.1145/2661735.2661737, dated August 2014.
- The reprint collects citations of its own: 198 works are linked to it and not to the GECCO record. A count for the paper should add the two records.

## 6. Independent searches for reproduction work (task 4) `[tool output]`

Titles of the top results were read; nothing was opened unless it is named below.

| # | Where | Query (shortened) | Hits | Top results read | Outcome |
|---|---|---|---|---|---|
| 1 | OpenAlex, title/abstract/keywords | (reproduce, reproduction, reproducibility, replicate, replication, reimplementation, re-run ...) AND (soft robot(s), voxel-based, virtual creatures) AND (evolution, evolving ...) | 118 | 25 | No reproduction of the 2013 study. Miconi & Channon 2005 (Sims re-implementation, already in note 4); a replication-data record for de Bruin et al. 2026 |
| 2 | OpenAlex, full text | "Unshackling evolution" AND the same reproduction words | 177 | 25 | None. The words also occur in their evolutionary sense, so this is noisy |
| 3 | OpenAlex, full text | "Unshackling evolution" AND phrases such as "replication study", "reproduce the results", "replicate the experiment", "reimplemented", "our implementation of" | 172 | 25 | None. Phrase matching is stemmed, so the count overstates |
| 4 | OpenAlex, full text | ("Cheney et al" OR "Unshackling evolution") AND (VoxCad OR Voxelyze) AND ("same parameters", "same settings", "following Cheney", "code provided by" ...) | 51 | 25 | Led to Sui et al. 2019; the rest known |
| 5 | OpenAlex, full text | dryad.m3s84 OR softbots2013 OR softbots2013Code OR softbotEvolution | 0 | - | No work in the full-text index names the deposit or the code archive |
| 6 | OpenAlex, semantic | a description of an independent reproduction of the 2013 experiment | 50 returned | 25 | The two records of the paper rank first; then Auerbach & Bongard 2010 and 2011, Medvet et al. 2021, Gu et al. 2019, Kimura et al. 2016. No reproduction |
| 7 | OpenAlex, title/abstract/keywords | (reproducibility, replication, replicability, reimplementation ...) AND (evolutionary robotics, evolved robots, robot evolution, morphological evolution, virtual creatures) | 824 | 20 | Nothing beyond the Sims re-implementations and data records |
| 8 | OpenAlex, title | (replication study, reproducibility study, replicating, reproducing, re-implementation, revisited) AND (artificial life, evolutionary computation, neuroevolution, genetic algorithm) | 119 | 25 | Lopez-Ibanez et al. 2021 and Da Ros et al. 2026 (both in note 4); a reproducibility study of a genetic-algorithm paper in chemistry (arXiv:2102.00700). Nothing on evolved robots |
| 9 | OpenAlex, title/abstract/keywords | VoxCad OR Voxelyze OR voxcraft OR evosoro | 10 | 10 | Gu et al. 2019; Ghosh et al. 2021; the evosoro paper; Sui et al. 2019 and 2022; a 2019 thesis from Zagreb; an Ogawa 2018 abstract. Few abstracts name the simulator at all |
| 10 | OpenAlex, semantic | a replication or reproducibility study in evolutionary robotics or artificial life | 50 returned | 15 | No replication of an evolved-robot experiment other than Miconi & Channon 2005 |
| 11 | Scite, search | (voxel-based soft robots, soft robot evolution, "Unshackling evolution", VoxCad, Voxelyze) AND (replication, reproducibility, reproduction study, reimplementation) | 87 | 20 | All known works; none a reproduction |

Class (e) remains as note 4 describes it: outside the Sims re-implementations there is no published replication study of an evolved-robot result, and Karns & Desell 2025 is still the only replication paper in the GECCO reproducibility track that the earlier survey found.

## 7. Open leads that need a person with Google Scholar or library access

1. **Gu et al. 2019**, DOI 10.1007/978-3-030-27535-8_3: read the chapter. Does it repeat the 2013 setup (materials, lattice, generations, runs), and does it report distances that can be set against the deposit?
2. **Ogawa 2019**, DOI 10.1007/978-3-030-24202-2_9: simulator, materials, and whether a no-cost flat-ground condition is included.
3. **Haile et al. 2022**: resolve references [9] and [30] in the PDF (open access at TechRxiv); check whether a peer-reviewed version exists; note the exact settings they say they took over.
4. **La Cava & Moore 2018**: full text for the simulator, the settings, and the published values they call comparable.
5. **Kimura et al. 2016 and 2021**; **Marzougui et al. 2022**: simulator and settings.
6. **Google Scholar "cited by"** for both versions (it may show them as one merged entry) with search-within-citing for: reproduce, replicate, re-implement, re-run, Dryad, softbots2013, softbotEvolution, "same parameters". Also the Dryad record's own citation and download panel.
7. **The 33 dissertations** in the CSV (filter `type = dissertation`). A thesis chapter is a likely home of an unreported re-run. Candidates by title: van Diepen 2020, Conradie 2021, Collins 2022, Navez 2024, Lessin 2014, Cully 2015; also Powers 2023 (arXiv:2306.03757, listed as a preprint).
8. **The withheld Scite snippets** (section 1.6), above all the statement in the discussion of Hiller & Lipson 2014 and the five in Cheney et al. 2018. Cheney et al. 2018 is on arXiv and Hiller & Lipson exists as a 2012 preprint, so most of this is a reading task, not an access problem.
9. **Code hosts and course pages** (forks and issues of the authors' repository, class projects), which no scholarly index covers.
10. The **13 citing items** counted on the OpenAlex records but not listable, and the **8 Scite-only citing papers** (titles in the next section).

## 7a. Addendum, same day: the two unread candidates' abstracts

Read on the publisher's pages (link.springer.com) in a browser, after the sweep above was finished. The full texts are behind a paywall and remain unread, so leads 1 and 2 of section 7 stay open for the bodies of the chapters. `[abstract]`

- **Gu et al. 2019**, DOI 10.1007/978-3-030-27535-8_3. The abstract describes an application of the method: a CPPN encoding, bodies built and simulated in VoxCAD, and an evolutionary analysis of a four-legged walking soft robot, presented as showing that the method works. It does not say that the 2013 experiment was repeated or that results are compared with it. Its reference list cites the SIGEVOlution version of the 2013 paper, the 2015 follow-up and the Hiller and Lipson work. The code `a?` in the CSV rests on the title; on the abstract it reads as a use of the tools, not a reproduction.
- **Ogawa 2019**, DOI 10.1007/978-3-030-24202-2_9. A different method: bodies of several materials grown in a development stage and then moved in a locomotion stage, a neural network optimised with age-fitness Pareto optimisation, crawling on the ground and under water. Not a re-run of the 2013 task.

## 8. Smaller records

- Scite-only citing papers, absent from both OpenAlex lists `[tool output]`, none relevant by title: 10.1109/tepra.2013.6556350; 10.1002/adfm.201303288; 10.1037/ebs0000145; 10.1145/3319619.3322006; 10.30878/ces.v30n1a9; 10.1002/aisy.202200071; 10.1088/1757-899x/1292/1/012009; 10.1002/aisy.202300505. Eleven more Scite entries are preprint versions of works that are in the CSV under their published DOI.
- The pulled OpenAlex item is the arXiv copy (arXiv:1512.03744) of MacCurdy et al., ICRA 2016, which is in the list.
- Note 1 recorded 279 for the GECCO record on 18 November. On 24 November the counter on the record reads 287 and the listable set is 279 including the pulled item.
