# Literature notes 1 — Evolving 3D voxel-based soft robots: lineage, state of the art, which morphologies emerge, and when limbs emerge

Survey date: 18 November 2026. Scope: the Sims → Hiller/Lipson → Cheney → Corucci/Kriegman line, its 2022-2026 successors, and related rigid/modular results on "what shapes evolve".

## 0. How to read these notes

**Verification legend (one tag per paper)**

- `[FULL]` I opened the full text and read the relevant passages myself. Exact wording can be checked in the plain-text extract named in the entry (line numbers given).
- `[ABS]` I opened the abstract page or the HTML full text through the fetch tool, which returns a machine summary. Title, authors and date are confirmed; details are the tool's paraphrase and I did not re-read the sentences myself.
- `[BIB]` I opened only a bibliographic record (Semantic Scholar, Europe PMC, an author's publication page). Title, authors, venue and year are confirmed. Anything said about content comes from other papers that cite it, or is marked "from memory".
- `[UNVERIFIED]` no confirming page opened.

**Quotations.** I do not reproduce the authors' sentences here. Each statement is paraphrased and followed by a pinpoint (section, figure, or line numbers in a text extract) so the exact wording can be read at the source.

**Text extracts on disk.** Papers marked `[FULL]` were converted to text in
`C:\Users\dnasilowski\AppData\Local\Temp\claude\18945b1088fdddf1\3e80c87b-e006-49b0-85ab-036cd0dca0dd\scratchpad\lit1_text\`
(file names are given per entry). Three more are the project's own copies under `C:\SoftRobotEvolution\research_reference\extracted\`. The scratchpad is temporary; copy the folder if the extracts should be kept.

**Limits of this survey.**
- The shared web-search allowance ran out part-way. After that I could only open known addresses and follow citation lists; no further keyword searches were possible. Coverage of 2025-2026 is therefore based on (a) the complete Semantic Scholar list of papers citing Cheney et al. 2013 (all 376 records read), (b) the arXiv author listing for S. Kriegman, (c) one arXiv phrase query, and (d) the searches done before the limit.
- Publisher pages for PNAS, MIT Press, Springer and eLife refused automated access. Where that mattered I used arXiv, Europe PMC, bioRxiv or author-hosted PDFs instead.

---

## 1. Roots

### 1.1 Sims 1994 `[BIB]`
K. Sims. "Evolving virtual creatures." SIGGRAPH '94, pp. 15-22, 1994. DOI 10.1145/192161.192167.
Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/192161.192167 (record; abstract withheld by publisher).
- Method/findings (from memory and from how later papers describe it): rigid blocks joined by actuated joints, body and neural controller encoded in a directed graph, evolved together for swimming, walking, jumping, following.
- Morphologies: few-segment block creatures. Cheney et al. 2018 count a mean of about 6 segments in Sims' figures and say later surveys show no clear growth in size or complexity (extract `cheney2018_scalable.txt`, lines 101-111).
- Relevance: the reference point every later paper uses when it says evolved bodies have stayed simple.

### 1.2 Hiller & Lipson 2010 `[BIB]`
J. Hiller, H. Lipson. "Evolving amorphous robots." Artificial Life XII (ALIFE 12), Odense, pp. 717-724, 2010.
Opened: https://sites.google.com/site/jonhiller/hardware/soft-robots (author's page with the citation).
- First locomoting soft robots made of a free 3D distribution of two materials, one of which expands and contracts periodically. The author's own page labels the resulting machine a locomoting "blob robot".
- Relevance: the lineage starts with bodies that are, by their designer's own description, blobs.

### 1.3 Hiller & Lipson 2012 `[BIB]`
J. Hiller, H. Lipson. "Automatic design and manufacture of soft robots." IEEE Transactions on Robotics 28(2):457-466, 2012. DOI 10.1109/TRO.2011.2172702.
Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TRO.2011.2172702 (record) and the author page above.
- From a search-result copy of the abstract (not opened at the publisher): evolutionary design of freeform soft locomotion robots from volumetrically expanding material; one design was built from foam and its measured performance agreed with simulation to within about 15%.
- Relevance: origin of the two-material (active/passive) voxel body that Cheney et al. extend to four materials.

### 1.4 Hiller & Lipson 2014 (Voxelyze) `[BIB]` + project copy
J. Hiller, H. Lipson. "Dynamic simulation of soft multimaterial 3D-printed objects." Soft Robotics 1(1):88-101, 2014. DOI 10.1089/soro.2013.0010.
Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1089/soro.2013.0010. The project holds the earlier manuscript "Dynamic simulation of soft heterogeneous objects" (`Hiller_Lipson_2012_physics.txt`).
- The simulator (lattice of point masses with rotational inertia joined by beams, volumetric actuation, collision handling) used by essentially every 3D voxel study below.

### 1.5 Rieffel et al. `[BIB]` / `[ABS]`
- J. Rieffel, D. Knox, S. Smith, B. Trimmer. "Growing and evolving soft robots." Artificial Life 20(1):143-162, 2014. DOI 10.1162/ARTL_a_00101. Opened: Semantic Scholar record only. From memory: tetrahedral-mesh soft bodies in a game physics engine, grown with a generative grammar, evolved with muscle firing patterns; not voxel based. I could not open the abstract, so no morphology claims are made here.
- J. Rieffel, J.-B. Mouret. "Adaptive and resilient soft tensegrity robots." arXiv:1702.03258 (2017; journal version in Soft Robotics, 2018, from memory). Opened: https://arxiv.org/abs/1702.03258. Vibration-driven tensegrity robot with gaits found by a data-efficient learning method; fixed morphology.
- A 2015 GECCO Companion paper "Growing and evolving vibrationally actuated soft robots" appears in the citing list (DOI 10.1145/2739482.2768485); not opened.

### 1.6 Joachimczak, Suzuki, Arita `[BIB]`
M. Joachimczak, R. Suzuki, T. Arita. "Artificial metamorphosis: evolutionary design of transforming, soft-bodied robots." Artificial Life 22(3), 2016. DOI 10.1162/ARTL_a_00207.
Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1162/ARTL_a_00207 (record with abstract).
- Soft-bodied 2D animats grown from one cell by a developmental model; evolved to work in water and on land with a metamorphosis between two body/controller forms.
- Why it matters here: Cheney et al. 2016 quote this paper's observation that the final body appears within the first few hundred generations and the rest of the run only tunes control (extract `cheney2016_difficulty.txt`, lines 138-144). This is the first written report of early body convergence in soft-robot evolution.
- Related, in the citing list, not opened: "Fine grained artificial development for body-controller coevolution of soft-bodied animats" (ALIFE 14, 2014); "Improving evolvability of morphologies and controllers of developmental soft-bodied robots with novelty search" (Frontiers in Robotics and AI, 2015).

### 1.7 Bongard 2011 `[BIB]`
J. Bongard. "Morphological change in machines accelerates the evolution of robust behavior." PNAS 108(4), 2011. DOI 10.1073/pnas.1015390108.
Opened: Semantic Scholar record. From memory: rigid robots that begin legless and grow legs during life evolve walking faster and more robustly than robots with fixed legged bodies. Legs here are given by the designer; the paper is about developmental scaffolding, not limb emergence.

---

## 2. The Cheney line (3D voxels, CPPN-NEAT, Voxelyze)

### 2.1 Cheney, MacCurdy, Clune, Lipson 2013 `[FULL]` (project copy)
N. Cheney, R. MacCurdy, J. Clune, H. Lipson. "Unshackling evolution: evolving soft robots with multiple materials and a powerful generative encoding." GECCO '13, pp. 167-174. DOI 10.1145/2463372.2463404. Reprinted in ACM SIGEVOlution 7(1), 2014.
Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/2463372.2463404 (376 citations; OpenAlex W2120652436 lists 279); text read from `Unshackling_Evolution_Cheney_2013.txt`.
- Method: CPPN-NEAT bodies up to 10x10x10, four materials, fixed open-loop actuation, fitness = centre-of-mass displacement after 10 actuation cycles; 35 runs x 30 individuals x 1000 generations; four cost regimes.
- What emerged, per the authors:
  - Without a cost, bodies contain more voxels and more actuated voxels (lines 331-335; Fig. 10 caption, lines 439-445).
  - Six named gait classes. The blocky, hinge-like "L-Walker" is the class that is more common without a voxel cost; "Jitter", "Jumper" and "Wings" never appear in the no-cost runs (Fig. 11 caption, lines 465-472). Jitter and Jumper are described as often made mainly of one muscle material (lines 390-396).
  - Leg-like forms are shown as "other, less common" strategies: opposite-leg stepping, a trunk-like appendage, and a gallop that uses stiff material as bone in longer appendages (Fig. 13 caption, lines 509-515). The stiff material is said to be exploited only rarely (Fig. 14 caption, lines 544-547).
  - Different cost functions change body plans while final distance stays roughly equal (lines 320-331).
- Authors' own wishes for future work: obstacle environments (a robot that grew "teeth" to hook on rings, Fig. 15), explicit diversity methods, and accepted quantitative measures of complexity and naturalness (lines 560-598).
- Relevance: the paper's own figures already separate "no cost → fuller, blockier, more muscle" from "cost → other body plans". The project's Dryad count (about 97% single-foot champions without cost) quantifies something the paper only shows qualitatively.

### 2.2 Cheney, Clune, Lipson 2014 `[BIB]`
N. Cheney, J. Clune, H. Lipson. "Evolved electrophysiological soft robots." ALIFE 14, pp. 222-229, 2014. DOI 10.7551/978-0-262-32621-6-ch037.
Confirmed in the Semantic Scholar citing list and a search listing (PDF at uvm.edu/neurobotics, not opened).
- From how Cheney et al. 2016 describe it (extract `cheney2016_difficulty.txt`, lines 160-166): actuation driven by signals propagating through tissue, which allows travelling waves that the 2013 two-phase muscles cannot produce.

### 2.3 Cheney, Bongard, Lipson 2015 `[FULL]`
N. Cheney, J. Bongard, H. Lipson. "Evolving soft robots in tight spaces." GECCO '15, pp. 935-942. DOI 10.1145/2739480.2754662.
Opened: https://www.uvm.edu/neurobotics/pubs/pdf/2015_CheneyBongardLipson_EvolvingSoftRobotsInTightSpaces_GECCO.pdf → extract `cheney2015_tight.txt`.
- Method: 11-voxel-wide bodies in a cage with a small opening; multi-objective NEAT (reach or escape distance, and body size) with speciation kept; 30 runs.
- What emerged: bodies that span the cage and unfold or unroll an "arm" through the opening (Fig. 3 caption, lines 373-377; lines 429-439). Results vary a lot between runs (mean 140 voxels moved out, standard deviation 99; lines 409-418).
- Why: the environment (aperture) plus a size objective make elongated reaching structures useful.
- Relevance: an example where an environmental constraint, not flat ground, produces appendage-like structures; also an early admission of large run-to-run spread.

### 2.4 Cheney, Bongard, SunSpiral, Lipson 2016 `[FULL]`
N. Cheney, J. Bongard, V. SunSpiral, H. Lipson. "On the difficulty of co-optimizing morphology and control in evolved virtual creatures." ALIFE XV, pp. 226-233, 2016. DOI 10.7551/978-0-262-33936-0-ch042.
Opened: https://meclab.w3.uvm.edu/papers/2016_ALife_Cheney.pdf → extract `cheney2016_difficulty.txt`.
- Method: 7x7x7 bodies, two CPPNs (body; per-voxel phase offset plus a global frequency), 30 runs x 5000 generations; "freeze the body at generation g" experiments.
- Findings:
  - Body shape locks in before about generation 100, often on simple forms (Fig. 1 caption, lines 303-306). The final body appears on average at generation 558, the best controller at 2926 (lines 385-390).
  - The authors say that this early body convergence was read, wrongly, as diversity of results in their own 2013 paper (lines 145-149).
  - They conjecture that soft bodies are so compliant that almost any shape can move adequately on flat ground, so the body matters little for fitness (lines 449-456).
  - With an added term that minimises actuated voxels ("energy"), bodies look more complex than the "more fully occupied shapes" of the plain-distance runs (lines 457-463 and 474-482; Fig. 4 caption, lines 512-519).
- Relevance: the closest published precursor of project findings (1) and (5). It states that plain distance on flat ground gives filled shapes, that a cost term gives sparser ones, and it already uses "freeze the body, keep optimising control" as an analysis tool.

### 2.5 Cheney, Bongard, SunSpiral, Lipson 2018 `[FULL]`
N. Cheney, J. Bongard, V. SunSpiral, H. Lipson. "Scalable co-optimization of morphology and control in embodied machines." Journal of the Royal Society Interface 15(143):20170937, 2018. DOI 10.1098/rsif.2017.0937. arXiv:1706.06133.
Opened: https://arxiv.org/pdf/1706.06133 → extract `cheney2018_scalable.txt`.
- Method: 5x5x5 (and 10x10x10) bodies, separate CPPNs for body and for per-voxel phase/frequency; "morphological innovation protection" resets an age counter after a body mutation so that new bodies get time to re-tune control; 30 runs x 5000 generations.
- Findings:
  - Without protection the best bodies are variants of a filled cube without appendages, found by about generation 50 and often already present in the random initial population (lines 559-569).
  - With protection, several of the top runs converge on the same body, a robot with a front and a back "leg" (Fig. 4 caption, lines 620-626); at 10x10x10 all ten top runs converge on one body (Fig. 6 caption, lines 682-688).
  - Distances at 5x5x5: about 21.7 voxels without protection versus about 32 with; at 10x10x10 about 32.6 versus 60.7 (lines 429-452 and 633-642).
  - The authors remark that negative results on co-optimisation are widely experienced but rarely published (lines 73-78).
- Relevance: the strongest statement in the lineage that the cube is a local optimum reached almost immediately, and that leaving it needs a change to selection, not just more generations.

### 2.6 Methenitis, Hennes, Izzo, Visser 2015 `[FULL]`
G. Methenitis, D. Hennes, D. Izzo, A. Visser. "Novelty search for soft robotic space exploration." GECCO '15, pp. 193-200. DOI 10.1145/2739480.2754731.
Opened: https://ir.cwi.nl/pub/23805/23805D.pdf → extract `methenitis2015_novelty.txt`.
- Method: same four materials and VoxCad simulator; CPPN-NEAT from a public HyperNEAT package with the parameters of Cheney et al.; novelty search on 2D trajectories versus fitness search; 10 runs, population 30, 1000 generations; lattices 5^3, 7^3, 10^3; four gravity levels.
- Findings: novelty search equals or beats fitness search at every gravity level; most fitness-search runs are described as trapped in low-fitness local optima (lines 596-626).
- Morphologies by gravity (lines 685-751, 776-790): Moon — only hopping works, C-shaped hoppers using mostly passive material; Mars — hoppers plus some legged bodies; Earth — two- and four-legged gaits with animal-like footfall diagrams, and under novelty search a rolling "tumbleweed"; Jupiter — galloping with thicker legs, worm-like push-pull, short hoppers with more muscle.
- Relevance: an independent group, same simulator, reports legged forms and states that higher gravity favours legs. It is qualitative (figures of selected individuals), with no count of how many runs gave legs.

### 2.7 Mouret & Clune 2015 `[FULL]` (project copy) + `[ABS]`
J.-B. Mouret, J. Clune. "Illuminating search spaces by mapping elites." arXiv:1504.04909, 2015.
Opened: https://arxiv.org/abs/1504.04909; text read from `MAP-Elites_Mouret_Clune_2015.txt`.
- The soft-robot experiment is the Cheney domain: 10x10x10, four materials, VoxCad, CPPN bodies; map axes are fraction of voxels filled and fraction of stiff "bone" voxels (128x128 cells).
- Result (lines 986-1003): MAP-Elites has significantly higher coverage and reliability; for the single best robot there is no significant difference from a plain evolutionary algorithm or one with a diversity objective; MAP-Elites is significantly worse on "precision". Only 5-8 finished runs per treatment were available and the authors say so (lines 969-976).
- Morphology note (lines 1034-1048): along the 75%-filled column they describe a two-legged body whose back changes from soft tissue to bone.
- Relevance: project finding (3) (NEAT gives the better champion, MAP-Elites the better population) repeats this comparison on the same task. The original is under-powered and reports "no significant difference" for the champion, so a properly powered version is still an open contribution.

### 2.8 Gravina, Liapis, Yannakakis 2017 and 2018 `[FULL]`
- D. Gravina, A. Liapis, G. N. Yannakakis. "Exploring divergence in soft robot evolution." GECCO '17 Companion. DOI 10.1145/3067695.3076072. Opened: https://mail.antoniosliapis.com/papers/exploring_divergence_in_soft_robot_evolution.pdf → extract `gravina2017_divergence.txt` (title page read only).
- D. Gravina, A. Liapis, G. N. Yannakakis. "Fusing novelty and surprise for evolving robot morphologies." GECCO '18. DOI 10.1145/3205455.3205503. Opened: https://mail.antoniosliapis.com/papers/fusing_novelty_and_surprise_for_evolving_robot_morphologies.pdf → extract `gravina2018_fusing.txt`.
- Method (2018): the Cheney task in VoxCad with the simulation parameters of Methenitis et al. (gravity 27.6 m/s^2 downward, 0.4 s, 40 Hz actuation), population 30, 1000 generations, eight lattice sizes from 3^3 to 10^3, 90 runs per condition (lines 436-450).
- Findings: novelty+surprise search is the most efficient and robust; objective search and novelty search explore few cells of a (filled fraction, bone fraction) map; novelty search favours more filled bodies with more active material, surprise search less filled bodies with more passive material (lines 576-590).
- Relevance: the largest independent re-run of the Cheney task that I found (720 runs per algorithm). It is a re-use of the original simulator, not a re-implementation, and it does not compare its numbers with Cheney's.

### 2.9 La Cava & Moore 2018 `[BIB]`
W. La Cava, J. H. Moore. "Behavioral search drivers and the role of elitism in soft robotics." ALIFE 2018 (MIT Press). DOI 10.1162/isal_a_00044.
Opened: Semantic Scholar record (no abstract available). Content not verified; the title indicates a selection-method comparison in a soft-robot task.

### 2.10 Lehman et al. 2020 `[FULL]`
J. Lehman, J. Clune, D. Misevic, et al. (over 50 authors, including N. Cheney). "The surprising creativity of digital evolution: a collection of anecdotes from the evolutionary computation and artificial life research communities." arXiv:1803.03453; Artificial Life 26(2), 2020.
Opened: https://arxiv.org/pdf/1803.03453 → extract `lehman2018_surprising.txt`.
- Lines 464-478 and Fig. 3: in the Cheney et al. soft-robot system the simulator chose its time step from the number of voxels. Evolution produced bodies of only a few cells, which got a large time step; their bottom cells sank through the floor between steps and the corrective force acted as free energy, so the robots vibrated and drifted quickly. The system was then patched: more damping at ground contact, a larger minimum body size, and a changed time-step rule.
- Lines 798-805: the same system's inchworm and bone-supported gallop are given as examples of convergence with biology.
- Relevance: project finding (6) (a too-soft floor gives spurious scores and shapes) is a documented phenomenon in the very system being re-implemented. It also means the published 2013 results depend on unpublished contact and time-step patches; whether the deposited code contains them is worth checking.

---

## 3. Corucci / Kriegman line (evosoro, development, sim-to-real, xenobots)

### 3.1 Corucci, Cheney, Lipson, Laschi, Bongard 2016 (growth, material) `[FULL]`
F. Corucci, N. Cheney, H. Lipson, C. Laschi, J. Bongard. "Material properties affect evolution's ability to exploit morphological computation in growing soft-bodied creatures." ALIFE XV, pp. 234-241, 2016. DOI 10.7551/978-0-262-33936-0-ch043.
Opened: https://meclab.w3.uvm.edu/papers/2016_ALife_Corucci.pdf → extract `corucci2016_material.txt`.
- Method: plant-like soft robots (6^3 to 10^3) whose voxels grow or shrink near light sources; phototaxis task; soft (5 MPa) versus stiff (500 MPa) material, 20 runs each.
- Morphologies: symmetric bodies with relatively independent appendages. The authors add that this degree of regularity is not common in similar settings and cite Cheney et al. 2013, 2015 and Methenitis et al. 2015 (lines 443-451).
- Relevance: a statement by co-authors of the Cheney line that limbs/regular appendages were uncommon in the earlier locomotion work.

### 3.2 Corucci et al. 2016 (swimming, 2-page abstract) `[FULL]`
F. Corucci, N. Cheney, H. Lipson, C. Laschi, J. Bongard. "Evolving swimming soft-bodied creatures." ALIFE XV late-breaking abstract, 2016.
Opened: https://www.uvm.edu/neurobotics/pubs/pdf/2016_CorucciCheneyLipsonLaschiBongard_EvolvingSwimmingSoftBodiedCreatures_ALIFE.pdf → extract `corucci2016_swimming.txt`.
- VoxCad with a per-facet drag model; multi-objective CPPN-NEAT with four objectives (distance, fewer actuated voxels, fewer voxels, young age). Preview of the 2018 journal paper.

### 3.3 Corucci 2017 (chapter) `[BIB]`
F. Corucci. "Evolutionary developmental soft robotics: towards adaptive and intelligent soft machines following nature's approach to design." In: Soft Robotics: Trends, Applications and Challenges, Springer, 2017. DOI 10.1007/978-3-319-46460-2_14.
Opened: Semantic Scholar record. Position/overview chapter; content not read.

### 3.4 Corucci, Cheney, Giorgio-Serchi, Bongard, Laschi 2018 `[FULL]` (project copy)
F. Corucci, N. Cheney, F. Giorgio-Serchi, J. Bongard, C. Laschi. "Evolving soft locomotion in aquatic and terrestrial environments: effects of material properties and environmental transitions." Soft Robotics, 2018. arXiv:1711.06605.
Opened: https://arxiv.org/abs/1711.06605; text read from `Soft_Locomotion_Aquatic_Terrestrial_Corucci_2018.txt`.
- Method: evosoro; two CPPNs (body; frequency and per-voxel phase); one material whose stiffness is fixed per experiment at 0.001, 0.01, 0.1, 1 or 10 MPa; three objectives (distance, fewer actuated voxels, fewer voxels) plus age; 15 runs x 5000 generations per condition; land, water, and land↔water switches.
- On land (lines 413-431, 459-487):
  - Fitness rises with stiffness up to 1 MPa.
  - Their scaling argument: at 1 MPa a rubber-density body deforms about 1.5% under its own weight, which permits legged support; at 0.1 MPa and below it deforms 15% or more, which prevents limb-supported locomotion.
  - Softest bodies collapse; 0.01 MPa bodies crawl and inch; 0.1 MPa bodies bounce and need much material to carry themselves; at 1 and 10 MPa bodies stand upright and walk.
  - The "branching index" rises with stiffness.
- Conclusion (lines 727-738): many four-legged walkers with clear limbs and symmetry, which the authors say were never seen in earlier work with the same simulator, encoding and algorithm; they suggest the three objectives as a possible reason.
- In water (lines 739-762): softer is faster; bodies grow tentacle-like, often passive, appendages and look alike across stiffness levels because of the simple fluid model. After a water→land switch, tentacles are shortened and reused as legs (Fig. 22 caption, lines 702-719).
- Run-to-run spread is called high and the algorithm "rather weak" (lines 651-654).
- Metric worth borrowing: branching index = 1 − (body volume / convex-hull volume), 0 for a full cube (lines 335-355); shape entropy of surface curvature after Auerbach & Bongard (lines 356-365).
- Relevance: the main published answer to "what makes limbs appear in this simulator": a stiffness-to-weight regime in which a leg can carry the body, together with material and energy objectives.

### 3.5 Kriegman, Cheney, Corucci, Bongard 2017 `[ABS]`
S. Kriegman, N. Cheney, F. Corucci, J. C. Bongard. "A minimal developmental model can increase evolvability in soft robots." GECCO '17. DOI 10.1145/3071178.3071296. arXiv:1706.07296.
Opened: https://arxiv.org/abs/1706.07296.
- Voxel robots whose bodies change over their lifetime by a fixed (not environment-driven) schedule; development lets evolution sample more body plans, later mutations stabilise the good ones. Conference precursor of 3.7.

### 3.6 Kriegman et al. 2017 (evosoro) `[BIB]`
S. Kriegman, C. Cappelle, F. Corucci, A. Bernatskiy, N. Cheney, J. C. Bongard. "Simulating the evolution of soft and rigid-body robots." GECCO '17 Companion. DOI 10.1145/3067695.3082051.
Opened: Semantic Scholar record. Describes the evosoro Python framework around Voxelyze (repository github.com/skriegman/evosoro, named in Corucci et al. 2018, footnote 2).

### 3.7 Kriegman, Cheney, Bongard 2018 `[FULL]`
S. Kriegman, N. Cheney, J. Bongard. "How morphological development can guide evolution." Scientific Reports 8, 2018. arXiv:1711.07387.
Opened: https://arxiv.org/pdf/1711.07387 → extract `kriegman2018_development.txt`.
- Method: a fixed 4x4x3 block of 48 voxels; evolution sets each voxel's resting length (bilaterally symmetric) and phase offset, either constant ("Evo") or changing linearly over the lifetime ("Evo-Devo"); flat ground, 40 actuation cycles, 30 runs x 10,000 generations.
- Findings (lines 170-173, 236-247, 305-312):
  - Two basins of attraction. A slower one of trotting or galloping four-legged bodies below 1 body length per second, and a faster one of rolling bodies at 5-6 body lengths per second.
  - 25 of 30 developmental runs reach the rolling design, against 6 of 30 non-developmental runs.
  - The authors explain legs as an incremental path: legs grow step by step because they reduce the area touching the floor, and thus friction.
  - The trot is called locally optimal, with body and control tightly coupled; rolling is far better on flat ground but is a needle in a haystack.
- Relevance: direct evidence, in this simulator, that on flat ground with a distance objective a legged body is a local optimum and a compact rolling body is the better solution. A project that hopes to "evolve limbs" on flat ground with distance fitness is asking evolution for the worse solution.

### 3.8 Kriegman, Cheney, Corucci, Bongard 2018 `[BIB]`
"Interoceptive robustness through environment-mediated morphological development." GECCO '18. arXiv:1804.02257. Confirmed in the arXiv author listing; not read.

### 3.9 Kriegman et al. 2019 `[ABS]`
S. Kriegman, S. Walker, D. Shah, M. Levin, R. Kramer-Bottiglio, J. Bongard. "Automated shapeshifting for function recovery in damaged robots." Robotics: Science and Systems 2019. arXiv:1905.09264.
Opened: https://arxiv.org/abs/1905.09264.
- A voxel robot recovers locomotion after damage (up to loss of all four legs) by changing its resting shape while keeping its controller. The four-legged starting body is designed by hand.

### 3.10 Kriegman et al. 2020 (sim-to-real) `[FULL]`
S. Kriegman, A. Mohammadi Nasab, D. Shah, H. Steele, G. Branin, M. Levin, J. Bongard, R. Kramer-Bottiglio. "Scalable sim-to-real transfer of soft robot designs." IEEE RoboSoft 2020. arXiv:1911.10290.
Opened: https://arxiv.org/pdf/1911.10290 → extract `kriegman2020_sim2real.txt`.
- Method: silicone voxel kit; the whole 2x2x2 design space of passive/active voxels evaluated in simulation; 108 shapes built, 9 actuated and measured.
- Findings (lines 380-404, 440-473): the two best designs in simulation and reality are a 2x2 plate with a one-voxel limb. They travel a similar net distance in both worlds but in opposite directions (the simulated robot pushes off the limb, the real one pulls with it). The authors blame the Coulomb friction model, which ignores contact area and adhesion, and warn about designs that exploit unrealistic properties of the simulation.
- Relevance: support for treating ground contact as the weak point of voxel simulation (project finding 6), and an example of exhaustive evaluation of a tiny design space as a method.

### 3.11 Kriegman, Blackiston, Levin, Bongard 2020 (xenobots) `[ABS]`
S. Kriegman, D. Blackiston, M. Levin, J. Bongard. "A scalable pipeline for designing reconfigurable organisms." PNAS 117(4):1853-1859, 2020. DOI 10.1073/pnas.1910837117.
Opened: https://pmc.ncbi.nlm.nih.gov/articles/PMC6994979/.
- Evolution of bodies from passive and contractile voxels (100 independent runs for locomotion), followed by a robustness filter (noise on actuation timing) and a build filter (not more than half muscle, no narrow concavities), then construction from frog cells.
- Morphologies: compact cell aggregates; the tool reported no mention of legs. The filters, not the search, remove muscle-dominated designs.
- Relevance: where this lineage needed sparse or non-all-muscle bodies, it imposed them with a constraint.

### 3.12 Kriegman, Blackiston, Levin, Bongard 2021 `[ABS]`
"Kinematic self-replication in reconfigurable organisms." PNAS 118(49):e2112672118, 2021.
Opened: https://pmc.ncbi.nlm.nih.gov/articles/PMC8670470/.
- Evolution of the parent shape that best gathers loose cells into offspring; shapes often converge on a C-shaped half-torus. 49 runs of 48 h on 8 GPUs. Not a locomotion-morphology study.

### 3.13 Other items in this line (not read)
- S. Kriegman et al. "Scale invariant robot behavior with fractals." RSS 2021, arXiv:2103.04876 `[BIB]`.
- D. Shah et al. "A soft robot that adapts to environments through shape change." arXiv:2008.06397 `[BIB]`.
- K. Horibe, K. Walker, S. Risi. "Regenerating soft robots through neural cellular automata." arXiv:2102.02579 (EuroGP 2021 per Semantic Scholar) `[ABS]`, https://arxiv.org/abs/2102.02579 — damaged simulated soft robots regrow their shape with local rules.
- K. Walker, H. Hauser. "Evolution of morphology through sculpting in a voxel based robot." ALIFE 2021, DOI 10.1162/isal_a_00418 `[BIB with abstract]` — evolves rules that remove voxels and change stiffness in response to the environment; the same rule yields different useful bodies in different environments.
- F. Pigozzi, S. Woodman, E. Medvet, R. Kramer-Bottiglio, J. Bongard. "Morphology choice affects the evolution of affordance detection in robots." GECCO 2023, DOI 10.1145/3583131.3590505 — title/authors from a search listing; PDF metadata confirms DOI only. Uses the GPU voxel engine voxcraft-sim (per the search listing).

---

## 4. Rigid and modular robots: what shapes evolve by default

### 4.1 Auerbach & Bongard 2014 `[ABS]`
J. E. Auerbach, J. C. Bongard. "Environmental influence on the evolution of morphological complexity in machines." PLOS Computational Biology 10(1):e1003399, 2014.
Opened: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003399.
- CPPN-encoded triangular-mesh bodies with simple oscillator control; flat ground versus 49 "icy block" terrains; complexity = entropy of surface curvature.
- Result: selection for displacement alone raises complexity in every environment, with no consistent environment effect. Only when simplicity is a second objective (a cost on complexity) do complex environments give more complex bodies than flat ground.
- Relevance: environment shapes morphology only when body complexity is costly; without a cost the environment signal is washed out.

### 4.2 Miras, Haasdijk, Glette, Eiben 2018 `[FULL]`
K. Miras, E. Haasdijk, K. Glette, A. E. Eiben. "Effects of selection preferences on evolved robot morphologies and behaviors." ALIFE 2018, pp. 224-231. DOI 10.1162/isal_a_00047.
Opened: https://www.mn.uio.no/ifi/english/people/aca/kyrrehg/publications/miras-alife2018.pdf → extract `miras2018_selection.txt`.
- Modular rigid robots with an L-system encoding; fitness = speed, speed with penalties, or novelty.
- Findings (lines 296-311, 462-511): the encoding itself tends to produce bodies with one or two long limbs. With speed alone the champions are near-identical single-limb robots and every one of them moves by rolling. A penalty on long limbs gives more limbs, more branching and more symmetry, and walking and rowing gaits.
- Relevance: the rigid-robot counterpart of "blob": speed on flat ground selects one simple body that rolls; limbs need an explicit morphological penalty.

### 4.3 Miras, Ferrante, Eiben 2020 `[ABS]`
K. Miras, E. Ferrante, A. E. Eiben. "Environmental influences on evolvable robots." PLOS ONE 15(5):e0233848, 2020.
Opened: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0233848.
- Flat floor: large, disproportionate, highly actuated bodies with few limbs that mostly roll. Floor tilted by 5 degrees: smaller, more proportionate bodies with more limbs that row or drag.
- Note: the request mentioned "snake-like" convergence. In the two Miras papers I opened the wording is "one or two limbs" and "rolling"; I did not find the word snake in the passages I read. A VU Amsterdam paper titled "Morphological attractors in Darwinian and Lamarckian evolutionary robot systems" exists (search listing only) and may be the source of that phrase `[UNVERIFIED]`.

### 4.4 Diversity methods versus plain evolution on bodies
- E. Medvet, A. Bartoli, F. Pigozzi, M. Rochelli. "Biodiversity in evolved voxel-based soft robots." GECCO '21. DOI 10.1145/3449639.3459315 `[BIB with abstract]`. 2D voxel robots; the representation matters more for diversity than the choice of evolutionary algorithm; no clear trade-off between diversity and effectiveness.
- E. Zardini, D. Zappetti, D. Zambrano, G. Iacca, D. Floreano. "Seeking quality diversity in evolutionary co-design of morphology and control of soft tensegrity modular robots." GECCO '21. arXiv:2104.12175 `[ABS]`, https://arxiv.org/abs/2104.12175. A NEAT-based method matches or beats MAP-Elites on task fitness; a two-map MAP-Elites variant fills the feature space best.
- F. Veenstra, M. H. Olsen, K. Glette. "Effects of encodings and quality-diversity on evolving 2D virtual creatures." GECCO '22 Companion. DOI 10.1145/3520304.3529053 `[BIB with abstract]`. MAP-Elites finds diverse solutions, but the encoding has the larger effect on performance.
- L. Eguiarte-Morett, W. Aguilar. "Premature convergence in morphology and control co-evolution: a study." Adaptive Behavior, 2023. DOI 10.1177/10597123231198497 `[BIB with abstract]`. Benchmarks quality-diversity algorithms on task performance and body diversity; reports that MAP-Elites balances exploration and exploitation but protects morphological diversity poorly. Robot type not confirmed.
- Relevance to finding (3): across substrates the recurring result is "plain or NEAT-style search is at least as good for the single best robot; quality-diversity is better for coverage", which is what the project found.

---

## 5. 2021-2026

### 5.1 Bhatia et al. 2021 (Evolution Gym) `[ABS]` + project copy
J. S. Bhatia, H. Jackson, Y. Tian, J. Xu, W. Matusik. "Evolution Gym: a large-scale benchmark for evolving soft robots." NeurIPS 2021. arXiv:2201.09863.
Opened: https://arxiv.org/abs/2201.09863. 2D voxel robots with reinforcement-learned control; the benchmark most 2022-2026 voxel papers use. Its contact model is penalty based (search summary, not re-read).

### 5.2 Biazzi, Fujita, Takahashi 2022-2024 `[FULL]`
R. B. Biazzi, A. Fujita, D. Y. Takahashi. "Convergent evolution in silico reveals shape and dynamic principles of directed locomotion." bioRxiv 10.1101/2022.11.20.516954 (version posted 14 May 2024); eLife Reviewed Preprint 87180.
Opened: https://www.biorxiv.org/content/10.1101/2022.11.20.516954.full.pdf → extract `biazzi2024_convergent.txt`; Europe PMC record. Version-of-record status at eLife not confirmed.
- Method: Voxelyze, 4x4x4 design space (controls at 6^3 and 8^3), CPPN and direct encodings, per-voxel phase offsets, one global stiffness chosen from 5e4 to 5e7 Pa, age-fitness Pareto selection, population 101, 1500 generations, 30 seeds per gravity level (9.81, 3.72, 0.1 m/s^2), fitness = mean speed over 30 s.
- Findings:
  - "Modules" are clusters of connected voxels that move in phase. The top 20% of robots have roughly 3 to 17 modules, sparsely connected; one or two modules are rare among the best (lines 386-398). High, mostly bilateral, symmetry.
  - Best stiffness is 5e7 Pa on Mars and Earth and 5e5 Pa in the water-like case (Methods, "Phenotype").
  - "Feet" = voxels of modules that touch the ground. Their share of the body shrinks as gravity rises, and robots with lighter feet keep their performance better when moved to higher gravity (Fig. 5 and lines 796-822).
  - Short evaluation windows reward bodies that launch and fall or curve; 30 s was needed to separate these from stable straight walkers (Methods, "Virtual environment simulation").
- Caveats: modules are defined by actuation phase, not geometry, so a solid block with several phase groups counts as multi-module. Code: github.com/biagzi/locomotion_principles.
- Relevance: the closest published work to the project's contact-patch analysis. It measures ground-touching parts in evolved Voxelyze robots, but with per-voxel phase control, evolved stiffness and a 30 s evaluation, and it concludes that appendages are selected. The project's single-foot result under two-phase muscles and a 10-cycle evaluation is a different regime and can be positioned against it.

### 5.3 Matthews, Spielberg, Rus, Kriegman, Bongard 2023 `[ABS, full text via Europe PMC]`
D. Matthews, A. Spielberg, D. Rus, S. Kriegman, J. Bongard. "Efficient automatic design of robots." PNAS 120(41):e2305180120, 2023. arXiv:2306.03263.
Opened: https://arxiv.org/abs/2306.03263 and https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10576117/fullTextXML.
- Method: a 2D sheet of elastic particles simulated with a differentiable material-point method. The start is a random rectangle with 64 voids (covering about 60% of the area on average) and 64 muscle patches; gradient descent moves and resizes voids and muscles; 10 design attempts, under 30 s on a laptop; 100 independent trials; one design built.
- Morphologies: from a limbless start the method consistently ends with two or three rear-angled appendages with muscle along their front edges. Legs form by voids merging into gaps between future limbs. Shape-only optimisation with fixed random muscles reached 0.31 body lengths/s, muscles-only 0.08, both together 0.45.
- Limits stated by the authors: local method, one behaviour, 2D.
- Relevance: the headline claim "legs emerge reliably" holds for a 2D, heavily perforated starting body under gradient descent. It is not evidence about 3D voxel evolution from random CPPNs.

### 5.4 Li, Matthews, Kriegman 2023 `[FULL]`
M. Li, D. Matthews, S. Kriegman. "Reinforcement learning for freeform robot design." arXiv:2310.05670 (v2, March 2024). Venue: ICRA 2024 from memory, not confirmed.
Opened: https://arxiv.org/pdf/2310.05670v2 → extract `li2023_rl_freeform.txt`.
- Method: a policy-gradient "designer" deposits or removes bundles of voxels on a 20^3 grid; Voxelyze-type physics; open-loop actuation; reward = horizontal distance in 5 s.
- Findings (lines 246-259): high-reward bodies have a low share of passive material, several active structures touching the ground, and high volume. Training increases body size and lowers the surface-to-volume ratio and the passive ratio.
- Relevance: an independent optimiser (reinforcement learning, not evolution) in the same physics drives bodies toward large, compact, mostly-muscle shapes under open-loop distance reward. This matches the "nearly all muscle, compact" half of project finding (1); it differs on contact (they report several contact structures).

### 5.5 Gradient-based topology optimisation of soft walkers
- C. Yuhn, Y. Sato, H. Kobayashi, A. Kawamoto, T. Nomura. "4D topology optimization: integrated optimization of the structure and self-actuation of soft bodies for dynamic motions." Computer Methods in Applied Mechanics and Engineering 414:116187, 2023. arXiv:2302.00905 `[ABS]`, https://arxiv.org/abs/2302.00905.
- H. Kobayashi, F. Gholami, S. M. Montgomery, M. Tanaka, L. Yue, C. Yuhn, Y. Sato, A. Kawamoto, H. J. Qi, T. Nomura. "Computational synthesis of locomotive soft robots by topology optimization." Science Advances 10:eadn6129, 2024. arXiv:2310.10985 `[ABS]`, https://arxiv.org/abs/2310.10985. Starts from a cube with a central cavity; material-point simulation; a walker and a climber were 3D printed; the abstract says limb-like structures result.
- H. Kobayashi, Y. Takaha, C. Yuhn, Y. Sato, S. Tomita, A. Kawamoto, T. Nomura. "Automated design of soft-rigid hybrid robots for dynamic locomotion." arXiv:2605.29389 (May 2026) `[ABS]`. Adds a stiff truss skeleton; the walking mode appears only with the skeleton.
- Also in the citing list, not opened: Sato et al., "Topology optimization of locomoting soft bodies using material point method" (arXiv:2203.16793); "Computational co-design of structure and feedback controller for locomoting soft robots" (arXiv:2407.09270).
- Relevance: in 3D, limb-like soft bodies are obtained today by gradient-based topology optimisation with a material-volume constraint, not by evolution. The 2026 result that a stiff skeleton is needed for walking echoes Corucci's stiffness finding.

### 5.6 Strgar, Matthews, Hummer, Kriegman 2024 `[ABS, HTML full text]`
L. Strgar, D. Matthews, T. Hummer, S. Kriegman. "Evolution and learning in differentiable robots." Robotics: Science and Systems 2024 (DOI 10.15607/RSS.2024.XX.100 per OpenAlex). arXiv:2405.14712.
Opened: https://arxiv.org/abs/2405.14712 and https://arxiv.org/html/2405.14712v2.
- Method: 2D mass-spring robots on a 13x22 triangular lattice; a genetic algorithm changes bodies, 35 gradient steps through a differentiable simulator train each body's neural controller; population 10,000, 1000 generations, about 10 million bodies, 4 H100 GPUs.
- Morphologies (tool summary): on flat ground bodies often evolve three or four legs; on rough ground two-legged bodies; a common local optimum is a tall unstable "leaning tower". The abstract lists premature convergence to simple bodies as one of the long-standing limits of the field.
- Statistics: ten runs in total; the crossover comparison rests on n = 2, which the authors state.
- Relevance: legs appear in 2D with learned closed-loop control and a compute budget four to five orders of magnitude above a single workstation.

### 5.7 Mertan & Cheney 2023-2025 (2D Evolution Gym)
- A. Mertan, N. Cheney. "Investigating premature convergence in co-optimization of morphology and control in evolved virtual soft robots." EvoApplications 2024 (EuroGP proceedings per Semantic Scholar). arXiv:2402.09231. `[FULL]` project copy `Mertan_Cheney_2024.txt`.
  - Bodies evolved under a fixed, sensor-free global actuation signal are found faster and score higher than bodies co-optimised with a learned controller. Under the fixed controller, run champions converge on the same body across runs: a mostly active base with two upright parts front and back (lines 296-318, 346-376). The abstract says evolved virtual soft robots lack complexity.
  - Relevance: the 2D source of the project's two-stage protocol. It reports convergence on one mostly-muscle body under a fixed gait, the 2D analogue of finding (1).
- A. Mertan, N. Cheney. "Evolutionary brain-body co-optimization consistently fails to select for morphological potential." arXiv:2508.17464 (v2, August 2026; submitted to Artificial Life). `[FULL]` project copy `Morphological_potential_2025.txt`. Exhaustively trains controllers for all 1,305,840 bodies of a small design space and shows that search discards newly mutated bodies that would have been better after training.
- A. Mertan, N. Cheney. "Modular controllers facilitate the co-optimization of morphology and control in soft robots." GECCO 2023, arXiv:2306.09358; "Towards multi-morphology controllers with diversity and knowledge distillation." GECCO 2024, arXiv:2404.14625; "Controller distillation reduces fragile brain-body co-adaptation and enables migrations in MAP-Elites." 2025 (venue not confirmed). Listings only `[BIB]`.
- A. Mertan, N. Cheney. "No-brainer: morphological computation driven adaptive behavior in soft robots." SAB 2024, arXiv:2407.16613 `[ABS]` (2D Evolution Gym, bodies evolved with MAP-Elites); "Morphological cognition: classifying MNIST digits through morphological computation alone." ALIFE 2025, arXiv:2508.17469 `[ABS]`.

### 5.8 Li, Kong, Kriegman 2024 `[ABS, HTML full text]`
M. Li, L. Kong, S. Kriegman. "Generating freeform endoskeletal robots." arXiv:2412.01036 (ICLR 2025 per Semantic Scholar).
Opened: https://arxiv.org/abs/2412.01036 and https://arxiv.org/html/2412.01036v1.
- Method: 3D bodies of soft voxels around rigid jointed bones on a 64^3 grid, compressed to a 512-dimensional latent space; evolution strategies over the latent space; a reinforcement-learned controller; population 64; 4 H100 GPUs for about 45 h per comparison.
- Morphologies (tool summary): on flat ground with a displacement reward the population becomes snake-like bodies with two joints, and evolution did not leave that local optimum in 100 generations. With a reward for upright locomotion the best design lifts its body on legs. With potholes, broad feet appear.
- Relevance: at the current frontier, flat ground plus displacement still collapses onto one simple body; legs were obtained by changing the reward or the terrain.

### 5.9 Strgar & Kriegman 2025 `[ABS, HTML full text]`
L. Strgar, S. Kriegman. "Accelerated co-design of robots through morphological pretraining." arXiv:2502.10862 (February 2025). A search snippet said "accepted at ICLR 2026"; not confirmed.
Opened: https://arxiv.org/abs/2502.10862 and https://arxiv.org/html/2502.10862.
- Method: 3D mass-spring robots built from a 6x6x4 voxel workspace; one controller pretrained by gradient descent over more than 10 million bodies; then bodies are evolved with that controller ("zero-shot evolution"), population 8192, 8 H100 GPUs.
- Findings (tool summary): the population converges on similar bodies that the shared controller handles easily ("diversity collapse"); fine-tuning the controller each generation restores diversity. Gaits are hopping; larger footprints help stability. The tool found no mention of legs.
- Relevance: the reverse order of the project's two-stage protocol (controller first, bodies second) and the same symptom, convergence on easy bodies.

### 5.10 Yu et al. 2025/2026 (modular legs) `[ABS, HTML]`
C. Yu, D. Matthews, J. Wang, J. Gu, D. Blackiston, M. Rubenstein, S. Kriegman. "Agile legged locomotion in reconfigurable modular robots." arXiv:2505.00784 (v1 May 2025 under the title "Reconfigurable legged metamachines that run on autonomous modular legs"; v3 February 2026). A Northwestern University news page (6 March 2026) says it appeared in PNAS; no DOI seen.
Opened: https://arxiv.org/abs/2505.00784, https://arxiv.org/html/2505.00784v3, https://news.northwestern.edu/stories/2026/03/evolved-robots-are-born-to-run-and-refuse-to-die.
- Rigid one-joint leg modules that attach freely. Body configurations are searched by Bayesian optimisation in an 8-dimensional learned latent space; policies trained in MuJoCo; three-, four- and five-module designs built and run outdoors.
- Relevance: here limbs are the building block, so they cannot fail to appear. It is also the Kriegman lab's use of MuJoCo, but for rigid modules, not voxel soft bodies.

### 5.11 Wang, Li, Guo, Kriegman 2026 `[ABS, HTML]`
Y. Wang, M. Li, Z. Guo, S. Kriegman. "ECo-MoE: embodiment-conditioned mixture of experts increases the evolvability of robots." arXiv:2605.24225 (May 2026).
Opened: https://arxiv.org/abs/2605.24225 and https://arxiv.org/html/2605.24225v1.
- Same endoskeletal 64^3 design space as 5.8; a mixture of control experts gated by the design's latent code; five runs per environment.
- Findings (tool summary): on flat ground with displacement reward the method falls into the same snake optimum as the baseline; gains appear for upright locomotion and potholes. The paper uses an "effective limb count" measure (one example scores 2.52 against 4 for a symmetric demonstration design).
- Relevance: confirms 5.8 two years later, and shows the lab now reports a numerical limb measure.

### 5.12 Other Kriegman-lab 2026 preprints `[ABS]`
- Z. Guo, S. Zhang, M. Li, P. Li, S. Kriegman. "Evolving dexterous robots from scratch." arXiv:2609.33101 (September 2026), https://arxiv.org/abs/2609.33101. Freeform bodies evolved for grasping and manipulation, printed and tested.
- Z. Guo, M. Li, S. Zhang, S. Kriegman. "Creating manufacturable blueprints for coarse-grained virtual robots." arXiv:2603.13582 (March 2026).
- C. Yu, S. Kriegman. "Robots that redesign themselves through kinematic self-destruction." arXiv:2603.12505 (March 2026).
- T. Hummer, S. Kriegman. "A non-cubic space-filling modular robot." arXiv:2403.01323 (2024), listing only.

### 5.13 Song et al. 2024-2026 (2D Evolution Gym) `[ABS]` + project copies
- J. Song, Y. Yang, Y. Xu, Y. Wen, W. Peng, G. Li, W. Zhou, W. Yao. "Shaping the evolutionary dynamics of robot morphology via adaptive control learning." arXiv:2608.23100 (2026). Project copy `AdaControl_2026.txt`. Too-short controller training before fitness evaluation biases selection toward fast-learning bodies and reduces body diversity; an adaptive training budget fixes this.
- J. Song et al. "Generative evolutionary design of voxel-based soft robots with provable optimality." arXiv:2609.29491; "RoboLDA: a probabilistic generative model for uncovering embodied hierarchical structures in voxel-based soft robots." arXiv:2609.29490. Both opened at arxiv.org/abs. The arXiv pages show a submission date of 24 August 2026 next to identifiers beginning 2609; I report them as displayed.
- J. Song et al. "MorphVAE." AAAI 2024. Project copy `MorphVAE_2024.txt`.

### 5.14 Singh 2025 `[BIB with abstract]`
R. Singh. "Evolutionary AI for morphological and locomotor design of resilient exploration robots." 9th International Conference on Computational System and Information Technology for Sustainable Solutions (CSITSS), 2025. DOI 10.1109/CSITSS67709.2025.11295732. A TechRxiv version dated February 2026 exists (search listing; the PDF refused access).
Opened: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/CSITSS67709.2025.11295732.
- CPPN-NEAT with novelty search under Earth, Mars and Moon gravity, in VoxCad per the search summary. Reports CPPN robots travelling 14.3 cm against 8.0 cm for a direct encoding under Earth gravity.
- Relevance: a recent re-run of the Cheney/Methenitis recipe in the original simulator. Single author, minor venue; not a re-implementation and, as far as the abstract shows, no comparison with the 2013 numbers.

### 5.15 Two Artificial Life and Robotics papers `[BIB]`
- C. Hahm. "Neuroevolution for vision-based seeking behavior in 3D soft voxel robots." Artificial Life and Robotics, 2025. DOI 10.1007/s10015-025-01019-z. NEAT versus HyperNEAT controllers for food seeking; simulator and body definition not confirmed (publisher page required sign-in).
- N. Shimaoka, R. Suzuki, T. Arita. "Investigating the effects of material ratio scenarios on soft robot design based on morphology-material-control coevolution." Artificial Life and Robotics 29(2):298-310, 2024. DOI 10.1007/s10015-023-00934-3. Opened: https://nagoya.repo.nii.ac.jp/records/2010974 (abstract). Material availability and rewards for using particular materials change the evolved structures; simulator not confirmed.

### 5.16 Other 2024-2026 voxel co-design papers, all 2D Evolution Gym or not voxel `[ABS]` or `[BIB]`
None of these studies 3D bodies, contact artefacts, or limb emergence.
- K. E. de Bruin, K. Glette, K. O. Ellefsen, G. Nadizar, E. Medvet. "Social learning strategies for evolved virtual soft robots." GECCO 2026, arXiv:2604.12482.
- L. Shen, K. Huang, W. Zhao, H. Liu. "EvoGymCM: harnessing continuous material stiffness for soft robot co-design." arXiv:2604.08258 (2026). Makes stiffness a continuous design variable.
- K. Harada, H. Iba. "Lamarckian co-design of soft robots via transfer learning." GECCO 2024, DOI 10.1145/3638529.3654180.
- D.-M. Zhang, C. Sun, R.-Y. Yin, Y.-K. Zhang, C. Chen. "Phased genetic algorithm for simultaneous morphology and controller optimization in soft robots." Discover Computing, 2026, DOI 10.1007/s10791-026-10490-6. "Phased" refers to an exploration/stabilisation schedule, not to body-then-control stages.
- J.-Y. Ren, X.-F. Liu, J. Zhang. "An actuator-aware genetic algorithm for soft robot design." ICIST 2026, DOI 10.1109/ICIST71072.2026.11727682.
- J. Wang, S. Pan, A. Serra-Gomez, X. Wei, Y. Xie. "Evolving embodied intelligence: graph neural network-driven co-design of morphology and control in soft robotics." arXiv:2603.19582 (project copy `GNN_codesign_2026.txt`).
- S. Zhang. "Nine trials to recover: a reproducible benchmark for repertoire-free soft-robot damage adaptation." arXiv:2610.07616 (October 2026), https://arxiv.org/html/2610.07616v1. 2D Evolution Gym, random 5x5 bodies, damage adaptation of actuator phases. Cites Cheney et al. 2013 only as background.
- J. R. Muff, K. Miras, A. E. Eiben. "Limits of Lamarckian evolution under pressure of morphological novelty." arXiv:2604.15854 (2026; submitted to WCCI 2026). Rigid modular robots; rewarding body diversity costs performance.
- K. Godin-Dubois, A. Yaman, A. V. Kononova. "Benefits of low-cost bio-inspiration in the age of overparametrization." arXiv:2604.20365 (2026). Controllers for a fixed quadruped.
- Y. Xie, K. Chu, X. Wang, F. Iida. "The morphology-control trade-off: insights into soft robotic efficiency." arXiv:2503.16127 (2025). Y. Zhang, Y. Xie, T. Sun, F. Iida. "Co-design is powerful and not free." arXiv:2510.08368 (2025).
- C. Chen, X. Xu, X. Wang, X. Huang. "Natural selection via foundation models for soft robot evolution." arXiv:2503.02249 (2025).
- L. Zhang. "CUDA-accelerated soft robot neural evolution with large language model supervision." arXiv:2405.00698 (2024), 3 pages.
- Checked and unrelated to voxel bodies: "Co-design Gym" (arXiv:2610.02366), "Microcosmos" (arXiv:2607.02954, 2D filaments in fluid), "Gradient-based co-design of systems and reinforcement learning policies with differentiable simulators" (arXiv:2611.19329).

### 5.17 Reviews and perspectives
- T. Howison, S. Hauser, J. Hughes, F. Iida. "Reality-assisted evolution of soft robots through large-scale physical experimentation: a review." Artificial Life 26(4), 2020. arXiv:2009.13960 `[ABS]`. A search summary of this review describes voxcraft-sim as a GPU re-implementation of Voxelyze.
- R. J. Alattas, S. Patel, T. M. Sobh. "Comprehensive survey of evolutionary morphological soft robotic systems." arXiv:1702.02934 (2017) `[ABS]`.
- Y. Wang et al. "Embodied co-design for rapidly evolving agents: taxonomy, frontiers, and challenges." arXiv:2512.04770 (2025) `[ABS]`. Survey of over a hundred co-design studies.
- M. Stölzle et al. "Soft yet effective robots via holistic co-design." arXiv:2505.03761 (2025, revised 2026) `[ABS]`. Perspective.
- R. Baines, F. Fish, J. Bongard, R. Kramer-Bottiglio. "Robots that evolve on demand." Nature Reviews Materials, 2024. DOI 10.1038/s41578-024-00711-z. Search listing only `[BIB]`.
- Y. Xie, Y. Zhang, T. Sun, F. Iida. "Energy as a common currency for understanding embodied evolution." Cyborg and Bionic Systems, 2026. DOI 10.34133/cbsystems.0680 `[BIB with abstract]`. Argues that judging evolved robots on task score alone hides energy cost and distorts conclusions about body and control complexity.
- T.-H. Wang et al. "SoftZoo: a soft robot co-design benchmark for locomotion in diverse environments." ICLR 2023. arXiv:2303.09555 `[ABS]`.

### 5.18 Physical voxel robots
J. Legrand, S. Terryn, E. Roels, B. Vanderborght. "Reconfigurable, multi-material, voxel-based soft robots." IEEE Robotics and Automation Letters, 2023. DOI 10.1109/LRA.2023.3236883 `[BIB with abstract]`. Self-healing polymer voxels assembled into a gripper and then a walker; physical behaviour within about 10% of simulation in the best case.

---

## 6. Has anyone replicated, re-implemented or re-analysed Cheney et al. 2013?

**Published, peer-reviewed, independent re-implementation of the physics with a comparison against the 2013 numbers: none found.**
**Published re-analysis of the deposited Dryad data: none found.**

What does exist:

| Kind | Item | What it is |
|---|---|---|
| Authors' lineage code | evosoro (3.6); voxcraft-sim (GPU engine, known here only from a review summary and a search listing) | Same group, same physics. |
| Re-use of the original simulator by other groups | Methenitis et al. 2015 (2.6); Mouret & Clune 2015 (2.7); Gravina et al. 2017, 2018 (2.8); Singh 2025 (5.14); Biazzi et al. (5.2, different task settings) | New search methods or conditions on Voxelyze/VoxCad. None reports a side-by-side reproduction of the 2013 fitness values or morphology frequencies. |
| Unpublished student term papers, Swarthmore College course CS81, autumn 2015, using the authors' source code | J. Segert, "Crawling before walking: improving walking soft robot evolution", https://www.cs.swarthmore.edu/~meeden/cs81/f15/papers/Julian.pdf (extract `segert2015_class.txt`) | 500 generations, duplicate runs. A plain-sigmoid NEAT matched CPPN-NEAT on peak fitness (69.43 versus 69.04 cm, lines 119-125). The author notes that a first run gave the opposite ranking and stresses replication. |
| | C. Cassidy, "Unshackling Unshackling Evolution: evolving softrobots with a multitude of materials", https://www.cs.swarthmore.edu/~meeden/cs81/f15/papers/Connor.pdf (extract `connor2015_class.txt`) | 5 runs x 300 generations per treatment. Reports that reproducing the four-material condition gave similar fitness curves, with mean peak 3.26 (lines 96-118). |
| Hobby code | Blog post "Softbot design with WANNs" (2020), https://joaogui1.netlify.app/post/softbot-design-with-wanns | Port of evosoro to Python 3 with weight-agnostic networks; early runs barely moved until bugs were fixed. |
| | GitHub "technocrat94/evolving-soft-robots" | A from-scratch 2D mass-spring toy; does not cite Cheney. |

One relevant warning for any re-implementation: section 2.10. The 2013 system was patched after evolution exploited floor penetration, and the paper itself does not state gravity, friction, damping or time-step settings (no such words occur in the paper text).

---

## 7. Synthesis — what the literature already establishes about blobs versus limbs

**A. Under distance-only fitness on flat ground, a compact, filled, muscle-rich body is the default outcome.**
1. Cheney 2013: no-cost runs use more voxels and more muscle; the blocky L-Walker dominates; legged gaits are the uncommon cases (2.1).
2. Cheney 2016: bodies lock in within about 100 generations on simple, largely filled shapes; soft bodies may be so compliant that shape hardly matters on flat ground (2.4).
3. Cheney 2018: without special protection the result is a filled cube without appendages, reached by generation 50 (2.5).
4. Corucci 2016: limb-like regularity "not common" in the earlier Cheney and Methenitis settings (3.1).
5. Li, Matthews, Kriegman 2023: a reinforcement-learning designer also grows large, compact, low-passive bodies (5.4).
6. Gravina 2018: novelty search favours more filled, more active bodies (2.8).
7. Mertan & Cheney 2024 (2D): a fixed gait gives the same mostly-active body in every run (5.7).
8. Li, Kong, Kriegman 2024 and Wang et al. 2026: flat ground plus displacement collapses onto one snake-like body (5.8, 5.11).
9. Miras 2018, 2020 (rigid modules): speed on a flat floor gives single-limb rolling bodies (4.2, 4.3).

**B. A legged body can be the worse solution.** Kriegman, Cheney, Bongard 2018: trotting four-legged bodies under 1 body length/s are a local optimum; rolling bodies reach 5-6 (3.7).

**C. Conditions reported to produce limbs or appendages**

| Condition | Evidence |
|---|---|
| Material and energy cost terms or objectives | Cheney 2013 (other body plans under costs); Cheney 2016 (energy term gives more complex shapes); Corucci 2018 (authors credit their three objectives); Auerbach & Bongard 2014 (environment effect only appears with a complexity cost); Miras 2018 (penalty on long limbs gives more limbs). In the xenobot pipeline a build filter caps muscle at half the body (3.11). |
| Stiffness high enough for a leg to carry the body under the chosen gravity | Corucci 2018 (about 1.5% self-weight deformation permits legs, 15% prevents them); Biazzi et al. (best stiffness rises with gravity); Kobayashi et al. 2026 (walking needs a stiff skeleton). |
| Gravity | Methenitis 2015 (hopping at Moon gravity, legs at Earth and above); Biazzi et al. (smaller feet at higher gravity). |
| Selection that shields new bodies while control re-adapts | Cheney 2018 (front-and-back-legged body). |
| Bodies that change size or grow | Kriegman 2018 (legs via voxel size differences, explained by friction reduction). |
| Environment other than open flat ground | Corucci 2018 (water gives tentacles, reused as legs after moving to land); Cheney 2015 (cage gives arms); Cheney 2013 Fig. 15 (obstacle rings give hooks); Li, Kong, Kriegman 2024 (potholes give broad feet); Miras 2020 (tilted floor gives more limbs). |
| Reward that names posture | Li, Kong, Kriegman 2024 (upright-locomotion reward gives legs). |
| Per-voxel phase control instead of two fixed muscle phases | Used in every study that reports legs after 2013 (Cheney 2016, 2018; Corucci 2018; Kriegman 2018; Biazzi). No study isolates this factor. |
| Gradient-based design | Matthews 2023 (2D, from a perforated sheet); Strgar 2024 (2D); Kobayashi 2024 (3D topology optimisation). |
| Limbs supplied as primitives | Yu et al. 2025/2026 (leg modules); grammar-based synthesis by van Diepen & Shea (J. Mechanical Design 2019 and 2022; search listings only `[BIB]`). |

**D. What is missing in all of the above.** Limb claims rest on pictures of selected individuals. Only Corucci 2018 (branching index), Biazzi et al. (modules, feet share), Miras (limb descriptors, rigid robots) and Wang et al. 2026 (effective limb count) give numbers, each with a different definition and none on the 2013 setup. No study varies the factors in table C jointly, and no study reports the fraction of runs that end limbed.

---

## 8. Overlap of 2024-2026 work with the project's six findings

| Project finding | Closest prior or concurrent work | Overlap |
|---|---|---|
| (1) Blobs, nearly all muscle, single contact patch; Dryad re-analysis shows the same without cost | 2.1, 2.4, 2.5, 3.1, 5.4 state the tendency in words or pictures. Biazzi et al. (5.2) measure ground-touching parts but in another regime and conclude the opposite about appendages. | Qualitative precedent is strong; the contact-patch census and the Dryad re-analysis are, as far as I found, new. |
| (2) Best score about 62% of Cheney's median | No independent benchmark exists. Only the two student re-runs with the authors' code (section 6). | Not scooped. |
| (3) NEAT gives the better champion, MAP-Elites the better population | Mouret & Clune 2015 on the same task (no significant champion difference, better coverage; 5-8 runs). Same pattern in Zardini 2021, Veenstra 2022, Eguiarte-Morett & Aguilar 2023. | Known pattern; a well-powered confirmation on this task is still missing. |
| (4) Seed-to-seed spread exceeds most "improvements" | Acknowledged in passing: Cheney 2015 (standard deviation of about 70% of the mean), Corucci 2018 (wide intervals), Strgar 2024 (n = 2 caveat), Segert's term paper. I found no voxel-robot paper that quantifies it as a result. | Open. Not searched exhaustively: search allowance ended before a dedicated query. |
| (5) Two-stage "body under fixed gait, then control on frozen bodies" gives sparse multi-material bodies | Mertan & Cheney 2024 (2D); Cheney 2016 freezing experiments (3D, as analysis); Strgar & Kriegman 2025 (reverse order, 3D mass-spring); Song et al. 2026 (control-training budget shapes body evolution, 2D). | No 3D voxel version found. |
| (6) Too-soft floor contact gives spurious scores and shapes | Lehman et al. 2020 anecdote about the same system (2.10); Kriegman 2020 on friction (3.10); Biazzi et al. on short evaluations rewarding launch-and-fall. | The phenomenon is documented as an anecdote; a controlled contact-stiffness sensitivity study is not. |

No 2024-2026 paper was found that re-implements the 2013 system in MuJoCo or any other engine, or that re-analyses its data.

---

## 9. Gaps a one-workstation project could fill (ranked)

1. **An independent reproduction and audit of the 2013 benchmark.** A second physics implementation, a comparison against the deposited champions, a numerical census of body types (contact patches, branching index, muscle share, filled share) for both the new runs and the Dryad data, and a sensitivity study of floor stiffness, damping and time step. Nothing like this is published; the only record of contact artefacts in this system is an anecdote.
2. **A controlled "when do limbs appear" experiment with a stated limb measure.** The literature attributes limbs to cost terms, stiffness-to-weight ratio, gravity, evaluation length, per-voxel phase control and selection scheme, each in a different setup and judged by eye. A small factorial study at 5^3 to 7^3 resolution over two or three of these factors, reporting the fraction of runs that end limbed, would be the first quantitative map. The Corucci deformation argument and the Kriegman rolling-versus-legs result give testable predictions.
3. **Statistical practice on this task.** A powered comparison of NEAT, MAP-Elites and the two-stage protocol in 3D with enough seeds to separate treatment effects from seed variance, reporting champion and population measures separately. Mouret & Clune's original comparison had 5-8 unfinished runs.

A caution that follows from 3.7 and 5.8: on flat ground with distance fitness, limbs are not what the objective asks for. A paper that explains why limbs do not evolve here, and under which measured conditions they do, is better supported by the literature than one that promises limbed robots.

---

## 10. Not verified, or verified only in part

- Publisher pages not reachable: PNAS (Matthews 2023 read through Europe PMC instead; Yu et al. journal version not seen), MIT Press (Rieffel 2014 abstract; La Cava & Moore 2018 abstract; Hiller & Lipson 2010 PDF), Springer (Hahm 2025; Shimaoka 2024 full text), eLife (Biazzi review pages and version-of-record status), TechRxiv (Singh 2026 version), IEEE (Hiller & Lipson 2012 abstract).
- Venues not confirmed at source: Strgar & Kriegman 2025 (ICLR 2026 per a search snippet); Li, Matthews, Kriegman (ICRA 2024 from memory); Yu et al. (PNAS per a university news page); Mertan & Cheney "Controller distillation" (GECCO 2025 not confirmed); Rieffel & Mouret (Soft Robotics 2018 from memory); journal volume/pages for Corucci 2018 and Kriegman 2018 not re-checked.
- Entries tagged `[ABS]`: details come from the fetch tool's summary of the page. This applies in particular to the morphology statements for Strgar 2024, Li/Kong/Kriegman 2024, Strgar & Kriegman 2025, Wang et al. 2026, Miras 2020, Auerbach & Bongard 2014 and the xenobot paper.
- "Snake-like" convergence in Miras et al.: wording not found in the two papers opened.
- voxcraft-sim: known here only through secondary mentions; its own record was not opened.
- van Diepen & Shea 2019/2022, Baines et al. 2024, Pigozzi et al. 2023: search listings only.
- Semantic Scholar labels ALIFE proceedings papers as "IEEE Symposium on Artificial Life"; venues above are given as ALIFE (MIT Press) where the DOI prefix is 10.1162/isal or 10.7551.
- Keyword searching stopped when the shared search allowance was used up. A dedicated search for (a) seed-variance studies in evolutionary robotics and (b) further 2026 conference papers (GECCO 2026, ALIFE 2026 proceedings) was not possible.
