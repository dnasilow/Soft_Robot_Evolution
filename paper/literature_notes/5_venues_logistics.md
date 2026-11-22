# Submission logistics: GECCO 2027, ALIFE 2027, journals, arXiv, affiliation

Research date: 18 November 2026. Every fact carries its source URL and a status label.

Status labels used below

- **[2027 confirmed]** read on the official 2027 page on 18 Nov 2026.
- **[2026 indication]** / **[2025 indication]** / **[2024 indication]** taken from an earlier edition; not a 2027 rule.
- **[verified]** read on the official page of the publisher or organisation.
- **[excerpt only]** the official page blocks automated access (HTTP 403 / bot check); the fact comes from search-engine excerpts of that official page and must be re-checked in a normal browser before relying on it.
- **[inference]** my reading, not stated on any page.
- **[not published]** nothing on the official page yet.

Access problems to know about: direct.mit.edu (Artificial Life, Evolutionary Computation, ALIFE proceedings), dl.acm.org (TELO guidelines, GECCO proceedings), royalsocietypublishing.org and journals.sagepub.com all answered with a bot check, so none of those pages was read directly. The web-search budget ran out near the end, so a few follow-up searches (noted where relevant) were not run.

---

## 1. GECCO 2027

Official pages read: https://gecco-2027.sigevo.org/ , https://gecco-2027.sigevo.org/Call+for+Papers , https://gecco-2027.sigevo.org/Important+Dates , https://gecco-2027.sigevo.org/Tracks , https://gecco-2027.sigevo.org/Track?itemId=51 (CS), https://gecco-2027.sigevo.org/Track?itemId=2672 (BBSR), https://gecco-2027.sigevo.org/Track?itemId=59 (NE), https://gecco-2027.sigevo.org/Organizers , https://gecco-2027.sigevo.org/Workshop+Proposals , https://gecco-2027.sigevo.org/Humies

### 1.1 Place, dates, format

- **[2027 confirmed]** Home page: "GECCO 2027 @ Kraków, Poland", "July 12 - 16, 2027", "— in person only —". https://gecco-2027.sigevo.org/
- **[2027 confirmed]** Call for Papers: "will be held in Krakow, Poland, from July 12 to July 16, 2027, and will present the latest high-quality results in genetic and evolutionary computation, in person only." https://gecco-2027.sigevo.org/Call+for+Papers
- Change from 2026: GECCO 2026 (San José, Costa Rica, July 13-17, 2026) allowed online presenters; 2027 does not. https://gecco-2026.sigevo.org/Registration

### 1.2 Deadlines (exactly as written on the official pages)

Table on the Call for Papers page **[2027 confirmed]** https://gecco-2027.sigevo.org/Call+for+Papers

| Category | Event | Date as written |
|---|---|---|
| Full Papers (Traditional) | Abstract Deadline | January 18, 2027 |
| Full Papers (Traditional) | Submission of Full Papers | January 25, 2027 |
| Full Papers (Traditional) | Notification of Acceptance/Rejection | March 19, 2027 |
| Full Papers (Traditional) | Camera-Ready Deadline | April 9, 2027 |
| Poster-Only Papers | Submission of Poster Papers | January 25, 2027 |
| Poster-Only Papers | Notification of Acceptance/Rejection | March 19, 2027 |
| Poster-Only Papers | Camera-Ready Deadline | April 9, 2027 |
| Presenter Registration | Author Registration Deadline | May 10, 2027 |

- The Important Dates page gives the same dates ("Abstract submissions for full papers: January 18, 2027", "Full paper submission: January 25, 2027", "Poster-only submission: January 25, 2027", "Notification of paper acceptance/rejection: March 19, 2027", "Camera-ready: April 9, 2027", "Presenter mandatory registration: May 10, 2027") plus "Tutorial, Workshop proposals: November 24, 2026" and "Tutorials, Workshops notifications: December 22, 2026". **[2027 confirmed]** https://gecco-2027.sigevo.org/Important+Dates
- Both paper deadlines are called "non-extensible": "Mandatory abstract submissions of at most 200 words for full papers are due by the non-extensible deadline of January 18, 2027; submissions of the full papers themselves are due by the non-extensible deadline of January 25, 2027." **[2027 confirmed]**
- **Time zone: not stated** on the Call for Papers page or the Important Dates page. **[not published]** Indications only: the 2027 Workshop Proposals page writes "November 24, 2026 (Anywhere on Earth)" for its own deadline (https://gecco-2027.sigevo.org/Workshop+Proposals); the GECCO 2026 late-breaking-abstract call wrote "April 3, 2026 (Anywhere on Earth)" (https://gecco-2026.sigevo.org/Call+for+LBAs). Third-party trackers that show "AoE" for the paper deadlines say they applied their own default. Treat AoE as unconfirmed; ask gecco2027@sigevo.org or submit a day early.
- **Conflict noted:** WikiCFP lists "Abstract Registration Due Jan 19, 2027", submission "Jan 26, 2027", notification March 20, final April 10 (http://www.wikicfp.com/cfp/servlet/event.showcfp?eventid=201407&copyownerid=13149). These do not match the official page; the official dates are January 18 / January 25 / March 19 / April 9.

### 1.3 Length, template, supplementary material

- **[2027 confirmed]** "Full papers of at most 8 pages (excluding references)". "Any content/appendix beyond the 8 pages limit (excluding references) should be submitted as supplementary material." So references do not count; an appendix inside the PDF does count; anything extra goes into supplementary material.
- **[2027 confirmed]** Abstract of at most 200 words, submitted first.
- **[2027 confirmed]** Poster-only papers: "at most 4 pages (including references)"; no abstract step; "All conditions for the submission of full papers also apply to poster-only papers." Published in the Companion Proceedings.
- **[2027 confirmed]** Template: "Authors using LaTeX should use:" the acmart class with "dvipsnames, format=sigconf, anonymous=true, review=true".
- **[2027 confirmed]** Supplementary: "Authors may submit additional supplementary material (e.g., videos, PDF appendix, data, mathematical proofs) alongside the PDF. All supplementary material must also be anonymized at submission time." File formats and size limit are not stated for 2027.
- **[2026 indication]** Supplementary could be "a PDF, ZIP archive (.zip) or a compressed tarball (.tgz or .tar.gz)"; limit 10 MB (paper upload limit 25 MB); "The supplementary material may or may not be considered when evaluating the paper, at the discretion of the reviewers." https://gecco-2026.sigevo.org/Call+for+Papers , https://gecco-2026.sigevo.org/Paper%20Submission%20Instructions
- **[2026 indication]** "You MUST use this ACM template" (SigConf; LaTeX or Word; US Letter); Type 1/TrueType fonts only, all embedded (matplotlib: pdf.fonttype and ps.fonttype 42); CCS Concepts and Keywords mandatory. Same instructions page.
- **[2026 indication]** Submission system was Linklings: https://ssl.linklings.net/conferences/gecco/ . The 2027 page does not name the system. **[not published]**

### 1.4 Review model and anonymity

All **[2027 confirmed]**, https://gecco-2027.sigevo.org/Call+for+Papers :

- "Each paper submitted to GECCO will be rigorously reviewed in a double-blind review process."
- "Anonymization: Submitted papers must NOT contain any element that reveals author identity (names, affiliations, acknowledgments, or self-referential language)."
- "Dual / Simultaneous Submission: Simultaneously submitting substantially similar work to another conference or journal is NOT ALLOWED. Submitting work already accepted or published elsewhere is also NOT ALLOWED (except for Hot Off the Press track)."
- "arXiv Submissions: Simultaneous submission of work to arXiv is permitted as a notable exception. Reviewers will not actively search for arXiv preprints."
- "Papers exceeding page limits, violating dual-submission rules, or out of scope will be rejected without review."
- Review criteria include "if applicable, sufficiency of information to permit replication."
- **Public code repositories:** the 2027 page has **no sentence about pre-existing public repositories**. What it does say: supplementary material must be anonymized, and a new code step (next item).
- "Submission of Code (New)": "This year we plan to pilot an initiative for greater transparency and reproducibility of manuscripts submitted to GECCO. While the details of this initiative will be communicated later, ... all papers for which code is a central aspect of the reported results will be expected to be accompanied by runnable code that could reproduce the manuscript's main results for the peer-review process. The code will only be accessed by authorised organisers for the sole purpose of verifying reproducibility. The presentation of the code or the level of commenting will not be inspected." Details are **[not published]**.
- **[2026 indication]** Self-citation wording: "any references to any of the author's own work should be made as if the work belonged to someone else." The 2026 call also encouraged "making the code available in a publicly accessible repository with a declared plan to enable permanent accessibility (e.g. zenodo)" while requiring "At the time of submission, all the supplementary material must also be anonymized." https://gecco-2026.sigevo.org/Call+for+Papers

### 1.5 Tracks and chairs for 2027

**[2027 confirmed]** https://gecco-2027.sigevo.org/Tracks

| Track | Chairs |
|---|---|
| BBSR - Benchmarking, Benchmarks, Software, and Reproducibility | Diederick Vermetten, Pascal Kerschke |
| CS - Complex Systems | Travis Desell, Sylvain Cussat-Blanc |
| ECOM - Evolutionary Combinatorial Optimization and Metaheuristics | Niki van Stein, Francisco Chicano |
| EML - Evolutionary Machine Learning | Penousal Machado, Bing Xue |
| EMO - Evolutionary Multiobjective Optimization | Carlos ignacio Hernandez Castellanos, Elizabeth Wanner |
| ENUM - Evolutionary Numerical Optimization | Anne Auger, Dirk Arnold |
| GA - Genetic Algorithms | Carlos Coello Coello, Gabriela Ochoa |
| GECH - General Evolutionary Computation and Hybrids | Emma Hart, Peter A. N. Bosman |
| GP - Genetic Programming | Gabriel Kronberger, Fabricio Olivetti de França |
| L4EC - Learning for Evolutionary Computation | Mario Andrés Muñoz, Elena Raponi |
| NE - Neuroevolution | Christian Gagné, Jialin Liu |
| RWA - Real World Applications | Yi Mei, Lie Meng Pang, Jorge Cruz, Julio Juarez Jimenez |
| SI - Swarm Intelligence | Ayah Helal, Efrén Mezura-Montes |
| THEORY - Theory | Martin Krejca, Johannes Lengler |

**Best fit: CS - Complex Systems.** **[2027 confirmed]** https://gecco-2027.sigevo.org/Track?itemId=51 . Chairs: Travis Desell (Rochester Institute of Technology, USA), Sylvain Cussat-Blanc (Université Toulouse Capitole, IRIT - CNRS UMR5505, Institut Universitaire de France). Description, quoted:

- "This track invites all papers addressing the challenges of scaling evolution up to real-life complexity. This includes both the real-life complexity of biological systems, such as artificial life, artificial immune systems, and generative and developmental systems (GDS); and the real-world complexity of physical systems, such as evolutionary robotics and evolvable hardware."
- "Evolutionary Robotics and Evolvable Hardware study the evolution of controllers, morphologies, sensors, and communication protocols ..."
- "The track welcomes contributions addressing problems from control to morphology, from single robot to collective adaptive systems."
- "Contributions are expected to deal explicitly with Evolutionary Computation, with experiments either in simulation or with real robots."
- The description does not use the words "soft robot" or "voxel"; the fit is through evolutionary robotics, morphology and GDS (CPPN encodings). **[inference]**

**Alternative: BBSR.** **[2027 confirmed]** https://gecco-2027.sigevo.org/Track?itemId=2672 . Chairs: Diederick Vermetten (Sorbonne Université, CNRS, LIP6), Pascal Kerschke (TU Dresden). Scope includes "Reproducibility studies that rigorously replicate published experiments with a substantial shift in confidence in the results of the original study" and "Innovative software and toolboxes for developing, evaluating, deploying, or teaching genetic and evolutionary computation in original and unique ways." The page ends: "we invite the authors to get in touch with the track chairs if in doubt about the suitability of their submission to this track." This fits the validated re-implementation part of the paper; the morphology and body-first vs co-optimisation studies fit CS better. **[inference]**

**Other tracks checked:** NE lists "Evolutionary robotics" and "Artificial life" only as application areas (https://gecco-2027.sigevo.org/Track?itemId=59). GECH is about hybrids of EC algorithms (https://gecco-2027.sigevo.org/Track?itemId=57). EML does not mention robots (https://gecco-2027.sigevo.org/Track?itemId=53).

**Track rules** **[2027 confirmed]**: "at most CEILING(40% * N_submitted_to_track) papers shall be accepted as a full paper"; "There is no maximum acceptance rate on poster papers submitted as poster papers nor on poster papers submitted originally as full papers" (so a full-paper submission can end up accepted as a poster); "Authors are responsible for selecting the most appropriate track"; papers may be transferred between tracks or desk rejected before reviewing starts.

**Size of the CS track (official accepted lists, each page states its total and is not paginated):** 5 of 149 full papers in 2026 (https://gecco-2026.sigevo.org/Accepted+Papers), 8 of 181 in 2025 (https://gecco-2025.sigevo.org/Accepted-Papers), 7 of 178 in 2024 (https://gecco-2024.sigevo.org/Accepted-Papers). CS posters: 7 in 2026, 4 in 2024 (2025 poster list is split over two pages; only the first was read). The number of CS submissions is not published on these pages, so the track's acceptance rate is unknown; the counts show a small track with few full-paper acceptances per year. **[verified counts; the reading is inference]**

### 1.6 Generative AI policy

All **[2027 confirmed]**, section "ACM and GECCO Authorship and Peer Review Policies on Generative AI (Updated)", https://gecco-2027.sigevo.org/Call+for+Papers :

- "Any use of AI tools to support the execution of the research (including, e.g., the implementation of code, design and analysis of experiments, generation of results, or any other aspects of the research lifecycle that are directly relevant to the conclusions of the research underlying the work) must be disclosed and described in detail in the Methods (or equivalent) section of the manuscript. This includes the creation of any artifacts that are directly relevant to the conclusions of the research, such as code, datasets, and charts or figures that rely on the AI tools."
- "Use of AI tools to support the writing of a submission should be explicitly mentioned in the Acknowledgments section, including the name of the tool and a short description of how it was used."
- "Generative AI / LLM tools cannot be listed as authors. All named authors remain fully responsible for the entire content of the paper, including all text, figures, and references."
- "Wholesale generation of text (as opposed to using AI to support and refine writing) is not allowed - particularly, but not exclusively, in the related works / state of the art / literature review sections - and could result in desk rejection if detected. For instance, the detection of hallucinated or misused references (i.e., references that do not relate to the statement for which they are being cited) may result in summary desk rejection."
- "Any attempt at prompt injection is strictly forbidden and will result in desk rejection."
- Reviewers "must not upload or share submitted manuscripts or review materials with generative AI systems."

ACM's own policy, for comparison **[verified]**, ACM Policy on Authorship, "Updated on May 14, 2026", https://www.acm.org/publications/policies/new-acm-policy-on-authorship : AI used to conduct the research (explicitly including "coding ... running simulations, data analysis") "must be described in detail in the methods section of the Work"; "When using Artificial Intelligence to assist with writing an ACM submission, ACM no longer requires the disclosure". GECCO 2027 is therefore stricter than ACM on writing help: it still asks for an Acknowledgments note. Practical point **[inference]**: the Acknowledgments section is removed in the anonymous submission, so the AI-use statements for code go in Methods at submission time, and the writing-tool note is restored at camera-ready (ask the chairs if unsure).

### 1.7 Other submission routes

- **Poster-only paper** **[2027 confirmed]**: 4 pages including references, January 25, 2027, same double-blind rules, Companion Proceedings.
- **Hot Off the Press, Late-Breaking Abstracts, workshop papers, competitions for 2027: [not published].** The 2027 menu has only Papers, Tutorial Proposals, Workshop Proposals, Humies. The Workshop Proposals page gives workshop-paper dates only as "Approx February - to be confirmed" (opening), "Approx April - to be confirmed" (deadline and notification), "Approx May - to be confirmed" (camera-ready). https://gecco-2027.sigevo.org/Workshop+Proposals
- **[2026 indication] Late-Breaking Abstracts**: opening "March 2, 2026"; deadline "April 3, 2026 (Anywhere on Earth)" (extended); notification "April 28, 2026"; camera-ready "May 5, 2026"; "2 pages using ACM template (including references)"; "briefly examined for relevance and minimum standards of acceptability, but will not be peer reviewed in detail"; poster presentation; Companion Proceedings; paid registration required. https://gecco-2026.sigevo.org/Call+for+LBAs
- **[2026 indication] Hot Off the Press**: for "their own work recently published in well-respected conferences and journals"; the paper "must not have been published in its final form earlier than 2025"; deadline "April 3, 2026"; notification "April 28, 2026"; "2 pages using ACM template". Not usable for unpublished work; usable later for a published journal version. https://gecco-2026.sigevo.org/Call+for+HOPs
- **[2026 indication] Workshop papers**: opening February 2, 2026; deadline moved from March 27 to April 3, 2026; notification April 26, 2026; camera-ready May 5, 2026; "must not exceed 8 pages (excluding references)"; blind review depends on the workshop. https://gecco-2026.sigevo.org/Call+for+Workshop+Papers . 2026 workshops included "BENCH@GECCO26 - Good Benchmarking Practices for Evolutionary Computation", "Open Source Software for Evolutionary Computation" and "Evolving Self-Organisation"; none on evolutionary robotics or soft robots. https://gecco-2026.sigevo.org/Workshops
- **[2027 confirmed]** 2027 workshop paper types: "Full papers (8 pages + references) - Author must cover the ACM Open APC", "Extended Abstracts (4 pages) - No APC required". https://gecco-2027.sigevo.org/Workshop+Proposals

### 1.8 Attendance, registration and publication cost

- **[2027 confirmed]** Author obligations: "Register at least one author before May 10, 2027 to attend the conference (as an in-person). Attend the conference (at least one author) in person. Present the accepted paper at the conference in person." "Each accepted paper requires at least one author registered. If an author is presenting more than one paper at the conference, they do not pay any additional registration fees."
- **2027 registration fees: [not published].**
- **[2026 indication]** Fees in USD (https://gecco-2026.sigevo.org/Registration): Regular, member 800 early-bird (by May 11, 2026) / 900; Regular, non-member 900 / 1000; "Student or Retiree / Unaffiliated", member 475 / 575, non-member 600 / 700. The page defines only the student condition ("Only students of bachelor, master, or Ph.D. programs with a valid student ID ..."); what "Unaffiliated" requires is not defined. "ACM SIGEVO Membership is available for 25 USD." If no author registers by the deadline "the submission will not be included in the proceedings."
- **Open-access charge (APC)** **[2027 confirmed]** on the GECCO call and **[verified]** on ACM's page: "All ACM publications, including those from ACM-sponsored conferences, are 100% Open Access." "Authors from institutions not participating in ACM Open will need to pay an APC to publish their papers, unless they qualify for a financial or discretionary waiver." 2027 subsidised rate: "$500 APC for ACM/SIG members", "$750 for non-members". ACM's table: ACM Conference Article, 2027: $750 ("No ACM or SIG Members"), $500 ("At Least 1 ACM or SIG Member"). https://authors.acm.org/open-access/initiatives-services-authors-site
- **[verified]** Waivers are unlikely for an independent author: "simply stating an inability to pay an APC as a result of being a graduate student or independent consultant without an affiliated institution is not itself a demonstration of financial hardship and is unlikely to be approved." ACM Policy on APC Waivers for Financial Hardship, updated December 17, 2025, https://www.acm.org/publications/policies/policy-on-discretionary-open-access-apc-waivers
- **[verified]** ACM Open coverage depends on the corresponding author's "primary affiliation (the institution where most of the research was conducted)" and an institutional email address. https://authors.acm.org/open-access/initiatives-services-authors-site . An unaffiliated author is not covered. **[inference]**
- **Poster-only papers and the APC:** not stated on the 2027 call. **[2026 indication]** "APC charges apply to accepted Full Papers, but Abstracts (1-2 pages), Extended Abstracts (1-4 pages) and Tutorials ARE NOT APC Eligible"; accepted poster-only papers "will appear as extended abstracts". https://gecco-2026.sigevo.org/Call+for+Papers . So a 4-page poster paper probably carries no APC, but this is unconfirmed for 2027.
- **Rough cost of an accepted full paper for an unaffiliated author [inference, 2026 fee levels]:** APC $500 (with a $25 SIGEVO membership, if SIG membership alone qualifies as the ACM table suggests) or $750, plus registration (about $475 to $1000 at 2026 levels, depending on whether the "Unaffiliated" row applies), plus travel to Kraków.

### 1.9 Reproducibility, artifacts, people

- No artifact badge programme is described on the 2027 pages. **[2027 confirmed: absent]** What exists: the "Submission of Code (New)" pilot (1.4), the BBSR track (1.5), and the review criterion on replication (1.4).
- Organizers **[2027 confirmed]** https://gecco-2027.sigevo.org/Organizers : General Chair Aniko Ekart (Aston University, UK); Editor-in-Chief Nelishia Pillay (University of Pretoria, South Africa); Proceedings Tea Tušar (Jožef Stefan Institute, Slovenia); Integrity Felipe Campelo (University of Bristol, UK); Local Chairs Szymon Łukasik and Piotr A. Kowalski; Workshops James McDermott and Ignacio Hidalgo. No Hot off the Press, LBA or reproducibility chair is listed yet.
- Contact **[2027 confirmed]**: gecco2027@sigevo.org
- Humies **[2027 confirmed]**: entry deadline Friday, May 28, 2027. https://gecco-2027.sigevo.org/Humies

---

## 2. ALIFE 2027

### 2.1 What is confirmed for 2027

- **[2027 confirmed]** Prague, Czech Republic; "July 19th, 2027 - July 23rd, 2027"; website https://2027.alife.org/ . The "Submission deadline" field is blank. https://alife.org/conference/alife-2027/ , https://alife.org/conferences/
- **[2027 confirmed]** https://2027.alife.org/ redirects to https://alife.vscht.cz/ : "July 19—23, 2027", "Organized by the University of Chemistry and Technology Prague (UCT Prague) & Czech Technical University". The About page notes the 40th anniversary of the ALIFE series. The Program page says: "ALIFE 2027 is still in the early planning stage, and the conference program has not yet been developed." https://alife.vscht.cz/about , https://alife.vscht.cz/program
- **[2027 confirmed]** General Chair: Jitka Čejková (UCT Prague), announced at the ALIFE 2026 closing ceremony; "Some positions on the organizing committee are still open." https://droplets.vscht.cz/news/260821announcement
- **Call for papers, deadlines, formats, template, review model, in-person or hybrid: [not published].**

### 2.2 Earlier editions as indication

**ALIFE 2026** (Waterloo, Canada, and online, 17-21 August 2026) **[2026 indication]** https://2026.alife.org/call-for-papers/

- "Full Papers & Summaries: Submission 30 March 2026 12 April 2026 (Extension – Anywhere on Earth)"; "Full Papers & Summaries: Notification 7 June 2026"; "Camera-Ready Papers: 21 June 2026"; "Late-Breaking Abstracts Submission deadline: 20 July 2026"; "Late-Breaking Abstracts Notification: 27 July 2026".
- "Full Papers are 3 to 8 pages long (not including references or acknowledgements) and should report on new, unpublished work. ... Accepted papers will be published by MIT press as open access conference proceedings. Accepted submissions will be assigned an oral or poster presentation."
- "Summaries summarize a previously published work. These are limited to a maximum of 2 pages (not including references or acknowledgements). ... If the work has only been published as a preprint it should be submitted as a full paper. Summaries will not be included in the proceedings."
- "Late Breaking Abstracts are limited to a maximum of 2-pages (not including references)"; not in the proceedings; posters.
- Review: "NB: Submissions are NOT anonymous. Include author names, affiliations, and, if appliciable, funding information. ALIFE 2026 has a single-blind review process."
- "Registration and presentation (in-person or online) is required for all accepted full papers to be included in the proceedings." Author registration by June 21, 2026, in person or online. https://2026.alife.org/registration/ (fee amounts are not shown on that page).
- Templates: Overleaf https://www.overleaf.com/read/tzwbbdfxqdrw#3ddbfa ; LaTeX and Word files linked from the call. The call does not name them "MIT Press template"; the proceedings are published by MIT Press.
- AI policy: "An AI cannot be the coauthor of a paper"; "AI usage itself is not a reason for rejection"; "AI usage should be clearly disclosed in the acknowledgements, which do not count towards the page limit." https://2026.alife.org/publishing-policy/
- "Papers accepted into the Artificial Life Journal (MIT Press) are automatically accepted into the ALIFE 2026 program as oral presentations."
- Relevant sessions: special session "Co-design of Robot Morphology and Control" (organisers Kai Olav Ellefsen, Kyrre Glette, Ege de Bruin, Kevin Sebastian Luck; submissions due April 12, 2026; accepted papers in the main proceedings) and workshop "Virtual Creature Competition". https://2026.alife.org/workshops-sessions/ , https://www.mn.uio.no/ifi/english/people/aca/kaiolae/alife-2026-special-session-on-co-design-of-robot-m.html
- Proceedings link given by the conference site: https://direct.mit.edu/isal/isal2026/volume/38 (not readable by automated tools).

**ALIFE 2025** (Kyoto, 6-10 October 2025, with online component) **[2025 indication]** https://2025.alife.org/submit : "Extended Deadline for Full Papers and Summaries: 11 May 2025"; full papers 3 to 8 pages; "will undergo a double-blind review process"; "Please do not write authors' names until paper is accepted".

**ALIFE 2024** (Copenhagen, July 22-26, 2024) **[2024 indication]** https://2024.alife.org/ , https://2024.alife.org/call_paper.html : paper deadline April 3, 2024, extended to April 10 and then April 15, 2024 (AoE); notification May 15, extended to May 22, 2024; camera-ready and author registration June 12, 2024; full paper "8-page maximum length (not including references)"; extended abstract 2 pages; double-blind.

What this means for the plan **[inference]**:

- The review model changed between years (double-blind in 2024 and 2025, single-blind in 2026), so 2027 cannot be predicted.
- In the three earlier years the main deadline fell between late March and mid May, that is after GECCO's 2027 notification date (March 19, 2027). If Prague follows the same pattern, a rejected GECCO paper could be revised for ALIFE; the 2024 edition, also a July conference, had its final deadline on April 15. This is a pattern, not a 2027 date.
- Full papers have been 8 pages without references, the same size as GECCO, in a different template.

---

## 3. Journals (later options)

Cost background for all ACM journals **[verified]**: ACM is fully open access since January 1, 2026; from January 1, 2027 journal APCs "return to list pricing": Journal Article $1800 list, $1300 ACM/SIG member (2026 subsidised: $1450 / $950). https://libraries.acm.org/acmopen/apc-list-pricing , https://authors.acm.org/open-access/initiatives-services-authors-site

### 3.1 Artificial Life (MIT Press)

- Official guidelines: https://direct.mit.edu/artl/pages/submission-guidelines (bot check; **not read directly**).
- **[excerpt only]** Article types: Articles "typically of 6,000 to 12,000 words"; Reviews "typically of more than 12,000 words"; Letters "typically of less than 2,000 words"; Meeting Reports. LaTeX or Word; single column, double-spaced; Overleaf template https://www.overleaf.com/latex/templates/artificial-life-journal-submission-template/zhhhjdgvhryt . "Artificial Life requires that each author have a valid ORCID"; ScholarOne. MIT Press Research Data Policy and generative-AI policy apply (use must be labelled and cited).
- **[excerpt only]** Open access: optional after acceptance (hybrid). The MIT Press general page lists US$1,800 for hybrid journals; not confirmed for this journal. https://direct.mit.edu/journals/pages/open-access
- **Conference extension: confirmed by example.** arXiv:2508.17464 (Mertan and Cheney) states it is the author's accepted manuscript in Artificial Life (DOI 10.1162/ARTL.a.476) and an extended version of an ALIFE 2025 paper (DOI 10.1162/ISAL.a.891). https://arxiv.org/abs/2508.17464 . In the other direction, ALIFE 2026 gave journal papers automatic oral slots (2.2).
- Explicit replication article type: none found. Review model: not confirmed.
- Scope fit: highest. Voxel soft robots and brain-body co-optimisation appear there (example above). **[inference]**

### 3.2 Evolutionary Computation (MIT Press)

- Official guidelines: https://direct.mit.edu/evco/pages/submission-guidelines (bot check; **not read directly**).
- **[excerpt only]** Papers "8,000 to 12,000 words in length (maximum of 35 pages in the Evolutionary Computation LaTeX style, including references)"; Letters "a maximum of 6 pages"; Editorial Manager.
- **[excerpt only]** Has published special sections of extended papers invited from GECCO (for example volume 26, issue 3) and a "Special Issue on Reproducibility" (Evolutionary Computation 32(1), editorial at https://direct.mit.edu/evco/article-abstract/32/1/1/119437/Editorial-for-the-Special-Issue-on-Reproducibility). A written rule on how much new material an extension needs was not found.
- Open-access fee: not confirmed (general MIT Press hybrid figure US$1,800). Explicit replication article type: none found. Review model: not confirmed.

### 3.3 ACM Transactions on Evolutionary Learning and Optimization (TELO)

- Official guidelines: https://dl.acm.org/journal/telo/author-guidelines (bot check; **not read directly**).
- **[verified]** ACM announcement, September 7, 2021, https://www.acm.org/media-center/2021/september/telo-inaugural-issue : "TELO will publish high-quality original papers in all areas of evolutionary computation and related subjects"; applications named include "robotics" and "the open-ended evolution of complex systems"; "papers submitted to TELO for publication will go through a rigorous double-blind reviewing process"; the board "will award ACM Reproducibility Badges to papers in the three categories of "Artifacts Available" (source code available in public archival repository), "Artifacts Evaluated" (documented, complete and exercisable), and "Results Reproduced" (results can be obtained from provided code)"; "a 10-member reproducibility board". Linked to SIGEVO.
- **[excerpt only]** Guidelines: "acmsmall" single-column format, author-year citations; ORCID before submission; badge requested in the cover letter, artifacts checked by the Reproducibility Board after the first review round; extended conference papers discussed in terms of "30 percent new material", where appendices or arXiv-only extensions can count as new unless already in proceedings or companions. Page limit: not found.
- **[verified]** ACM general rule for a revised version of a published paper: "at least 25% of the paper is material not previously published", the editor must be told, and the venues' policies must allow it. https://www.acm.org/publications/policies/simultaneous-submissions . Also: "providing an explanation of the incremental contribution of a journal paper that extends prior results published in a conference paper. (In cases of double- anonymous review, this information should be supplied to the editor or program chair only.)" https://www.acm.org/publications/policies/new-acm-policy-on-authorship
- Cost **[verified]**: no ACM Open cover for an unaffiliated author, so $1800 (or $1300 with ACM/SIG membership) from January 1, 2027.
- Explicit replication paper type: none found. The reproducibility badges are the journal's distinctive feature.

### 3.4 IEEE Transactions on Evolutionary Computation (TEVC)

All **[verified]** on https://cis.ieee.org/publications/t-evolutionary-computation/tevc-information-for-authors and https://cis.ieee.org/publications/t-evolutionary-computation/tevc-page-charges :

- Scope: "archival quality original papers in evolutionary computation and related areas including nature-inspired algorithms, population-based methods, and optimization where selection and variation are integral ... application papers that provide general insights into these areas of computation."
- "TEVC publishes three types of articles: regular papers, letters, and survey papers. Letters are normally 6 pages or less." Three reviews (two for letters). No replication type; "Comments on Published Papers" exist.
- Anonymous submission: "must not include the names nor the affiliations of its authors."
- Length and charges: "mandatory over-length page charge for pages in excess of 10 pages for a regular paper"; "$200 (per page)"; maximum "15 pages for a regular paper". Voluntary page charge of $110 per page "not obligatory".
- Open access: hybrid; "US$2800 for articles submitted in 2026".
- "All IEEE journals require an Open Researcher and Contributor ID (ORCID) for all authors."
- Conference versions: "conference papers and book chapters that have been published previously are not acceptable unless until they have been enhanced significantly."
- Preprints: "it is fine to post to arXiv with certain conditions."
- AI: "The use of AI-generated text in an article shall be disclosed in the acknowledgements section".
- Submission: https://ieee.atyponrex.com/journal/TEVC-IEEE
- Fit **[inference]**: algorithm-focused and very selective; a replication plus morphology study is a harder sell than at Artificial Life or TELO.

### 3.5 Soft Robotics (SoRo; formerly Mary Ann Liebert, now Sage)

- The Liebert author page now redirects (HTTP 301) to journals.sagepub.com. **[verified redirect]** https://home.liebertpub.com/publications/soft-robotics/616/for-authors . Sage guidelines: https://journals.sagepub.com/author-instructions/srb (bot check; **not read directly**).
- **[excerpt only]** Scope: "soft and deformable robots", covering flexible electronics, materials science, computer science and biomechanics. A "4,000-word limit for Original Research Articles and Review Articles" (abstract, references, tables and legends excluded). A "submission fee: $49". Preprints accepted if declared. Open-access option exists; fee not found. The excerpts conflict on abstract length (250 vs 350 words).
- Fit **[inference]**: weak for a simulation-only evolutionary study; the journal centres on physical soft robots and materials.

### 3.6 IEEE Robotics and Automation Letters (RA-L)

All **[verified]** on https://www.ieee-ras.org/publications/ra-l , https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-authors/ , https://www.ieee-ras.org/publications/ra-l/submission-procedures/ , https://www.ieee-ras.org/publications/rules-for-the-double-anonymous-review-process/ :

- "Letters will be six pages long, with at most two extra pages allowed at a charge ($175 per extra page)"; page limits include "figures, tables, and any appendices".
- "a final decision on any manuscript within 6 months from submission"; double-anonymous review.
- Open access optional: "US$2645 for articles submitted in 2025, and US$2800 for articles submitted in 2026". ORCID required for all authors.
- "The RA-Letters will not consider submissions that are currently under review for a conference." Earlier conference papers must be "explicitly cited" with a statement of the differences.
- Accepted papers can be presented at ICRA, IROS, CASE or RoboSoft within a transfer window listed on the journal page.
- Anonymity rules: "no links to external websites that reveal identity" (YouTube, GitHub, institute pages); anonymised links are fine and the page names anonymous.4open.science; "Authors are allowed to use tools such as arXiv"; "Reviewers should not actively search for those articles to identify authors."
- Fit **[inference]**: possible for a concise, robotics-facing result; six pages is tight for a replication plus three studies.

### 3.7 Frontiers in Robotics and AI

All **[verified]** on https://www.frontiersin.org/journals/robotics-and-ai/about , https://www.frontiersin.org/journals/robotics-and-ai/for-authors/article-types , https://www.frontiersin.org/journals/robotics-and-ai/for-authors/publishing-fees :

- Sections include "Soft Robotics", "Computational Intelligence in Robotics", "Robot Design", "Bio-Inspired Robotics".
- Article types and limits: Original Research 12,000 words (A-type); Methods 12,000 (A); Technology and Code 12,000 (A); Brief Research Report 4,000 (B); Registered Report (Stage 1: 3,000; full: 12,000; A). Replication studies are named under Registered Reports; Original Research and Brief Research Report may report non-reproducibility of published results.
- Fees: "A-Type Articles: CHF 2,195", "B-Type Articles: CHF 1,750"; fee-support programme "for authors and institutions with insufficient funding".
- Review: "We use the single anonymized peer review model"; editor and reviewer names are published. Fully open access. Shown metrics: 3.7 Impact Factor, 7 CiteScore.
- Conference extension policy: not checked.

### 3.8 Royal Society Open Science and Journal of the Royal Society Interface

- Journal sites (royalsocietypublishing.org) are behind a bot check; the facts below marked verified come from royalsociety.org.
- **[verified]** Royal Society Open Science is gold open access and "will remain gold open access"; APC "£1400", "$1960", "€1680" (no pricing year on the page); discretionary waivers exist for journals "where open access publication is the only option"; 25% saving with Open Access Membership. https://royalsociety.org/journals/open-access/ , https://royalsociety.org/journals/authors/subscribe-to-open-for-authors/
- **[verified]** A Replication article type exists at Royal Society Open Science since 2019, with results-blind review; the announcement describes it for psychology and cognitive neuroscience. https://royalsociety.org/blog/2019/04/celebrating-our-first-two-replication-articles
- **[excerpt only]** The journal's author page lists research articles, reviews, perspectives, Registered Reports, replications and others; the replication policy is written for the Psychology and Cognitive Neuroscience section; scope covers "all of science, engineering and mathematics"; review is on soundness. https://royalsocietypublishing.org/rsos/pages/for-authors , https://royalsocietypublishing.org/rsos/pages/replication-studies . Whether a robotics or computer-science replication may use the Replication type is **unconfirmed**; ask the editorial office.
- **[verified]** Journal of the Royal Society Interface: in 2026 under Subscribe to Open, authors publish open access "without having to pay an article processing charge (APC)", CC-BY by default; the model "is conditional" and journals may "revert to a hybrid open access model". 2027 status: not stated. https://royalsociety.org/journals/authors/subscribe-to-open-for-authors/
- **[excerpt only]** Interface research articles: more than 2,500 and not exceeding 8,000 words including cover page, references and acknowledgements; cross-disciplinary work between the life and physical sciences. https://royalsocietypublishing.org/rsif/pages/for-authors
- **[verified]** All Royal Society journals: "It is a requirement of Royal Society Publishing that data and code underlying a study are made publicly available"; the submitting author must provide an ORCID; AI use must be declared. https://royalsociety.org/journals/authors/author-guidelines/

### 3.9 ReScience C

All **[verified]** on https://rescience.github.io/ , https://rescience.github.io/write/ , https://rescience.github.io/board/ , https://rescience.github.io/read/ :

- "platinum open-access peer-reviewed journal that targets computational research" that "encourages the explicit replication of already published research"; promotes "new and open-source implementations". No fees are mentioned.
- Criteria: "Rigorous methodology", "Original source code", "Substantial evidence for replication of the original results" or an explanation of why not. "ReScience C accepts negative results as well."
- "you cannot submit the replication of your own research" (nor that of close collaborators). A third-party replication of Cheney et al. 2013 meets this condition. **[inference]**
- Process: LaTeX template (https://github.com/rescience/template), submission as a GitHub issue (https://github.com/rescience/submissions), two reviewers in the open, then "upload your code to Zenodo in order to get a DOI". Licence CC BY. For a failed replication the authors must have "attempted to contact the authors of the original article".
- Activity: Volume 11 (2026) has 2 articles so far; Volume 10 (2025) has 7.
- Board: no editor for robotics, evolutionary computation or artificial life; machine learning (Georgios Detorakis) and computer science (Nicolas P. Rougier) are the nearest; one listed reviewer names robotics.
- Limits **[inference]**: it publishes the replication itself, not the new studies; publishing the replication there and the same replication results in a GECCO paper would need care about prior publication (GECCO: "Submitting work already accepted or published elsewhere is also NOT ALLOWED").

### 3.10 Summary table

| Journal | Fit | Replication type | Typical length | Mandatory fee | Conference extension |
|---|---|---|---|---|---|
| Artificial Life | high | none found | 6,000-12,000 words [excerpt] | none found (OA optional) [excerpt] | yes, by example (ALIFE 2025 paper extended) |
| Evolutionary Computation | good | none found; reproducibility special issue 2024 [excerpt] | 8,000-12,000 words, max 35 pages [excerpt] | none found [excerpt] | GECCO special sections have existed [excerpt] |
| ACM TELO | good | none found; reproducibility badges [verified] | not found | $1800 / $1300 member from 2027 [verified] | yes, about 25-30% new material [verified ACM rule; excerpt for TELO] |
| IEEE TEVC | moderate | no | 10 pages, up to 15 at $200 each [verified] | none up to 10 pages; OA $2800 optional | only if "enhanced significantly" [verified] |
| Soft Robotics | weak | not found | 4,000 words [excerpt] | $49 submission fee [excerpt] | not found |
| IEEE RA-L | moderate | no | 6 pages, plus 2 at $175 each [verified] | none up to 6 pages; OA $2800 optional | differences must be stated [verified] |
| Frontiers in Robotics and AI | good | via Registered Report; non-reproducibility reports allowed [verified] | 12,000 words (4,000 brief) [verified] | CHF 2,195 (CHF 1,750 brief) [verified] | not checked |
| Royal Society Open Science | moderate | yes, but written for psychology section [verified + excerpt] | not found | £1400 [verified] | not found |
| J. R. Soc. Interface | moderate | no | 2,500-8,000 words [excerpt] | none in 2026 (S2O) [verified]; 2027 unknown | not found |
| ReScience C | exact for the replication part | yes, this is the whole journal [verified] | no limit found | none mentioned [verified] | not applicable |

---

## 4. arXiv

### 4.1 Endorsement policy today

All **[verified]**: https://info.arxiv.org/help/endorsement.html and https://blog.arxiv.org/2026/01/21/attention-authors-updated-endorsement-policy/

- "arXiv requires that users be endorsed before submitting their first paper to arXiv or a new category."
- Change of January 21, 2026: "As of January 21, 2026, arXiv will no longer accept institutional email addresses (i.e., an email address associated with an academic or research institution) as the sole qualifier of endorsement for new authors."
- "Endorsement for new submitters in all categories will now follow two paths. The first path requires both 1) an institutional email address from an academic/research institution and 2) previous authorship on an existing paper which has been accepted to the arXiv "endorsement domain" they wish to submit to ... New submitters who cannot meet these requirements can pursue the second path, which is seeking personal endorsement directly from an established arXiv author in the same endorsement domain."
- "arXiv staff cannot waive endorsement requirements or provide a personal endorsement for authors."
- First rolled out for Mathematics in December 2025: https://blog.arxiv.org/2025/12/10/updated-endorsement-policy-for-arxiv-mathematics/
- How to ask (help page): "Start a new submission and select the category you wish to submit to." An endorsement request email arrives with a link for prospective endorsers (the endorser enters "a six-character alphanumeric endorsement code"). Find candidates through the link "Which authors of this paper are endorsers?" at the bottom of the abstract pages of related arXiv papers. "You may include a link to your ORCID profile, other scholarly profile, or a copy of your intended submission if you are comfortable doing so." "it is inappropriate to email large numbers of potential endorsers at once, or to repeatedly email the same endorser". "At least one positive endorsement is required per endorsement category".
- Who can endorse: "Endorsers must have authored a certain number of papers within the endorsement domain of a subject area"; only papers "submitted between three months and five years ago" count; the endorser needs an active endorsement in that area. The number for computer science is not given on the page.
- Endorsers are told: "The endorsement process is not peer review. You should know the person that you endorse or you should see the paper that the person intends to submit."
- Endorsement domain: "most high-level subject areas (e.g., hep-th, cond-mat, q-bio) are currently endorsement domains, with the notable exception of physics". The page does not name "cs"; that cs.NE and cs.RO share one cs-wide domain is **[inference]**.

### 4.2 What this means for this author **[inference from the rules above]**

- No institutional email and no earlier arXiv paper: the first path is closed. An alumni address would not help, because the first path also needs prior arXiv authorship in the domain, and because arXiv requires the claimed affiliation to be current (4.4).
- The only route is a personal endorsement from an established arXiv author active in the area, obtained by showing the manuscript. Candidates are found through the endorser link on the abstract pages of the voxel-soft-robot papers the manuscript cites (section 8 lists several with arXiv IDs).
- Start the endorsement request well before the wanted posting date; nothing on the pages gives a processing time.

### 4.3 Other 2025-2026 changes

- **[verified]** October 31, 2025: in the CS category, review articles and position papers "must now be accepted at a journal or a conference and complete successful peer review" before submission. This concerns reviews and position papers, not research papers with new results. https://blog.arxiv.org/2025/10/31/attention-authors-updated-practice-for-review-articles-and-position-papers-in-arxiv-cs-category/
- **[verified]** October 1, 2026: "arXiv now limits submitters to up to two submissions per calendar month", "with a limit of three total active submissions at any given time"; applies "across all submitters and categories"; rejected submissions count. https://blog.arxiv.org/2026/10/01/updated-rate-limit-policy/
- **[verified]** January 13, 2026: updated policy for non-English papers in effect (listed on https://blog.arxiv.org/page/2/ ).
- **[verified]** AI tools: arXiv continues "to require authors to report in their work any significant use of sophisticated tools", including text-to-text generative AI; "generative AI language tools should not be listed as an author". A submission may be declined if it "lacks originality, novelty, significance". https://info.arxiv.org/help/moderation/index.html
- No blog post after January 2026 changes endorsement again (blog pages 1 to 3 checked on 18 Nov 2026). https://blog.arxiv.org/

### 4.4 Identity and affiliation on arXiv

**[verified]** https://info.arxiv.org/help/policies/identity_and_affiliation.html : "Claimed affiliation should be current in the conventional sense: e.g., physical presence, funding, e-mail address, etc." "It is a violation of our policies to misrepresent your identity or organizational affiliation. Misrepresentation of identity or affiliation, for any reason, is possible grounds for immediate and permanent suspension." Linking an ORCID is recommended.

### 4.5 Primary category

**[verified]** https://arxiv.org/category_taxonomy

- cs.NE (Neural and Evolutionary Computing): "Covers neural networks, connectionism, genetic algorithms, artificial life, adaptive behavior. Roughly includes some material in ACM Subject Class C.1.3, I.2.6, I.5."
- cs.RO (Robotics): "Roughly includes material in ACM Subject Class I.2.9."
- cs.AI: "Covers all areas of AI except Vision, Robotics, Machine Learning, Multiagent Systems, and Computation and Language".

Reading **[inference]**: by the descriptions, cs.NE is the natural primary category (genetic algorithms, artificial life) with a cross-list to cs.RO; cs.AI is excluded by its own wording. Observed practice differs: recent voxel-soft-robot papers use cs.RO as primary with cs.NE or cs.AI cross-lists (arXiv:2604.12482: cs.RO + cs.AI; arXiv:2504.06523: cs.RO + cs.LG + cs.NE; arXiv:2508.17464: cs.RO + cs.NE). Either is defensible; moderators can reclassify ("Reclassification by our moderators ensures that submissions are posted to the most relevant category").

### 4.6 arXiv and GECCO anonymity

**[2027 confirmed]** Posting is allowed during review ("Simultaneous submission of work to arXiv is permitted as a notable exception. Reviewers will not actively search for arXiv preprints."). ACM agrees: "Posting a pre-print version of the Work to arXiv or a similar pre-print venue is not considered a prior or current publication venue". https://www.acm.org/publications/policies/new-acm-policy-on-authorship

---

## 5. Affiliation norms

### 5.1 ACM and GECCO

- **[verified]** The ACM Policy on Authorship (updated May 14, 2026) has no rule on which affiliation to list. It requires authors to be identifiable humans ("Anonymous authorship is not permitted, although pseudonyms and/or pen names are permitted provided accurate contact information is given to ACM") and: "They will provide ACM with a valid ORCID prior to completion of the ACM eRights process". **So ORCID is required by ACM.** https://www.acm.org/publications/policies/new-acm-policy-on-authorship . The FAQ adds that the corresponding author is "responsible for obtaining ORCIDs from all listed co-authors". https://www.acm.org/publications/policies/frequently-asked-questions
- **[verified]** ACM defines the primary affiliation in its open-access guidance: "They must indicate their primary affiliation (the institution where most of the research was conducted). If an author has since moved institutions, a current address may also be included, but ACM will not update affiliations after publication." https://authors.acm.org/open-access/initiatives-services-authors-site
- **[verified]** acmart v2.21 (2026/11/01) documentation: "The fields \institution, \city and \country are mandatory." and "ACM strongly encourages that you include ORCIDs for all authors". https://raw.githubusercontent.com/borisveytsman/acmart/primary/acmart.dtx
- **[verified]** ACM's Policy on Plagiarism, Misrepresentation, and Falsification covers author misrepresentation (who is credited), not affiliation wording. https://www.acm.org/publications/policies/plagiarism-overview
- GECCO 2027 / SIGEVO pages: no affiliation rule beyond removing affiliations from the anonymous submission. **[2027 confirmed: absent]**
- No ACM page read here gives wording for authors without an institution. **[not found]**

### 5.2 COPE (ACM states it is a COPE member and follows COPE's authorship definition)

- **[verified]** COPE discussion document "Crediting organisations in scholarly publications" (last reviewed 9 September 2026; https://doi.org/10.24318/JOvfLlSA ), https://publicationethics.org/guidance/discussion-document/crediting-organisations-scholarly-publications :
  - "Organisations that did not make a substantial contribution to the work should not be listed or acknowledged as contributing entities, whether explicitly or implicitly. A contribution is considered substantial if the work as presented could not have been carried out without this support."
  - "The sole function of listing organisational addresses on the author byline is to provide contact details for the authors and their affiliated organisations at the time the research was conducted."
  - "Independent researchers: if an organisation contractually prohibits a researcher from using its name for unsupported work, authors should list themselves as independent researchers (no affiliation). In such cases, authors must demonstrate how the work met appropriate governance standards and identify who was responsible for its oversight."
  - "Past affiliations: if research was completed prior to an author's current contract, the byline should reflect the past affiliation in place when the work was carried out (annotated as a past affiliation)". This is about work done while at the earlier institution, not about alumni status.
  - "every author must provide contact details ... and a unique persistent identifier, such as an ORCID".
- **[verified]** COPE Case 26-24 (2026), "Can researchers with no institutional affiliation be authors?", https://publicationethics.org/guidance/case/can-researchers-no-institutional-affiliation-be-authors : "Journal policies should allow authors to list themselves as independent researchers (ie, with no affiliation). However, in such circumstances, authors must show how their work met appropriate governance standards, who was or is responsible for its oversight, and who is accountable." Editors may run "additional verification and integrity checks (eg, past publications and co-authorships, previous institutional affiliations ...)". A ban on unaffiliated authors "could still be perceived as discriminatory". The page notes this is case advice, "not formal COPE guidance".

### 5.3 Publishers

- **[verified]** Cambridge University Press, "Author affiliations" (last updated 22nd September 2021), https://www.cambridge.org/core/services/authors/author-affiliations :
  - 1a: "Any article affiliations should represent the institution(s) at which the research presented was conducted and/or supported and/or approved."
  - 1c: "your affiliation(s) should denote which institution(s) are accountable for the research."
  - 3b ("I'm an independent researcher/retired and I have no affiliation. How should I list my affiliation?"): "Where no institution provided direct support by means of funding, resources, oversight or other any other support to the work carried out, please input 'Independent Researcher' in the main manuscript file and in your user account if applicable."
- **[verified]** IOP Publishing: "If a researcher is not affiliated to an institution or company, they can list themselves as "independent researcher"." https://publishingsupport.iopscience.iop.org/questions/affiliated-institution/
- **[verified]** Taylor & Francis: "Your affiliation in the manuscript and when entered into the submission system should be the institution where you conducted the research." Affiliation cannot be changed to qualify for an open access agreement. https://authorservices.taylorandfrancis.com/editorial-policies/defining-authorship-research-paper/

### 5.4 University policy (one example; the author's own alma mater was not looked up)

- **[verified]** Durham University, Institutional Affiliation Policy (approved by Senate 27 January 2026): among its examples of unauthorised use is "A former member of the University continuing to use their Durham University" affiliation outside the policy's scope, for example "for papers reporting their own research not conducted in association with the University". https://dur.ac.uk/research/ethics--governance/institutional-affiliation-policy/
- Other policies seen in search results but not opened: University of Rochester, Imperial College (former students publishing work done at Imperial list Imperial, subject to department approval), University of Leicester. They concern work done at the university.

### 5.5 Answer

- An alumnus who did the work independently, without employment, enrolment, funding, supervision, resources or approval from the university, should **not** list the alma mater as affiliation. Sources: Cambridge 1a and 3b; COPE discussion document; ACM's definition of primary affiliation; arXiv's "current" affiliation rule; Durham as an example of a university treating such use as unauthorised. **[verified sources; the conclusion is my reading of them]**
- The accepted wording is "Independent Researcher" (Cambridge 3b, IOP, COPE). In acmart, where institution, city and country are mandatory, that gives `\institution{Independent Researcher}`, `\city{...}`, `\country{...}`. **[inference for the acmart form]**
- Listing an ACM Open member university as primary affiliation would also wrongly trigger an APC waiver; ACM ties that waiver to the institution "where most of the research was conducted". **[inference]**
- Alumni status belongs, if anywhere, in a biography or CV, not in the byline. COPE's document also says organisations that did not contribute should not be acknowledged. **[inference]**
- Expect integrity checks: COPE advises editors to verify unaffiliated authors through ORCID, earlier publications and governance statements. A public ORCID record, a public repository and an archived DOI help here. **[inference]**
- Remaining step: read the alma mater's own affiliation or name-use policy.

---

## 6. Double-blind practicalities

- GECCO 2027 rules that apply **[2027 confirmed]**: no identity-revealing element in the paper; supplementary material "must also be anonymized at submission time"; runnable code expected for review, read only by "authorised organisers", details to come; arXiv allowed. Nothing on the page forbids an existing public repository, and nothing mentions one.
- Reading **[inference]**: a public repository under the author's real name that existed before submission is not against any stated GECCO 2027 rule, provided the submitted PDF and supplementary files do not link to it or name it in an identifying way. The tolerance GECCO states explicitly ("Reviewers will not actively search") is written for arXiv preprints only. If the software has a distinctive name that leads straight to the repository, consider a neutral name in the review version. A one-line question to the track chairs or gecco2027@sigevo.org would settle it.
- Anonymous GitHub **[verified]**: public instance https://anonymous.4open.science/ ; source and README https://github.com/tdurieux/anonymous_github . It anonymises the owner, organisation and repository name and replaces "a configurable list of terms" in file contents; the README states the boundary is "the paper plus its online appendix — and only that." Named as acceptable in IEEE RAS's official double-anonymous rules ("You can use tools to anonymize them like" anonymous.4open.science), https://www.ieee-ras.org/publications/rules-for-the-double-anonymous-review-process/ . GECCO's pages name no tool.
- OSF view-only links with the Anonymize option **[excerpt only]**: "Select Anonymize if you want to hide contributor names (useful for blind review)"; it does not redact names inside files. https://help.osf.io/article/353-welcome-to-projects . An excerpt of a Center for Open Science document says existing private projects become read-only after February 19, 2027 during an "OSF transition"; check before relying on OSF for a January 2027 submission.
- Anonymised ZIP as supplementary material **[2026 indication]**: .zip or .tgz, 10 MB limit.
- Things to strip from an anonymised code copy **[inference]**: author names and emails in file headers, LICENSE, CITATION.cff, setup or pyproject metadata, README badges and URLs; the .git folder (commit authors); absolute paths containing a user name in logs, configs and notebooks; PDF and image metadata; DOIs pointing to a named Zenodo record.

---

## 7. Open-science infrastructure for the camera-ready

- **Zenodo with GitHub** **[verified]**: "Zenodo archives your repository and issues a new DOI each time you create a new GitHub release." https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content . Zenodo's own guide: enable the repository, describe the software with a CITATION.cff or Zenodo JSON file, archive by a GitHub release or manual upload; software records also go to Software Heritage. https://help.zenodo.org/docs/github/
- **Dryad** **[verified]**: "an open data publishing platform" for research data in all fields; partners with Zenodo for software and supplementary files. https://datadryad.org/stash/about . Fees were not on the page read.
- **OSF** **[verified]**: "a free open-source software project that facilitates open collaboration in science research" (Center for Open Science). https://help.osf.io/article/342-getting-started-on-the-osf
- **CITATION.cff** **[verified]**: "plain text files with human- and machine-readable citation information for software (and datasets)"; used by GitHub, Zenodo and Zotero. https://citation-file-format.github.io/ . GitHub shows a "Cite this repository" link when the file is in the root of the default branch; a `preferred-citation` block points citations to the paper. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files
- Figshare is named by GitHub's page as another archive.
- Venue expectations: GECCO 2026 recommended "a publicly accessible repository with a declared plan to enable permanent accessibility (e.g. zenodo)" **[2026 indication]**; TELO's "Artifacts Available" badge needs "source code available in public archival repository" **[verified]**; the Royal Society requires public data and code **[verified]**; ReScience C requires a Zenodo DOI for the code **[verified]**.

---

## 8. Recent accepted papers on evolved voxel soft robots and brain-body co-optimisation

Sources for venue and track: the official accepted lists https://gecco-2026.sigevo.org/Accepted+Papers , https://gecco-2026.sigevo.org/Accepted+Posters , https://gecco-2025.sigevo.org/Accepted-Papers , https://gecco-2025.sigevo.org/Accepted-Posters , https://gecco-2024.sigevo.org/Accepted-Papers , https://gecco-2024.sigevo.org/Accepted-Posters , and the ALIFE 2024 programme https://2024.alife.org/detailed_program.html . Run counts come from the arXiv full texts where one exists.

| # | Venue, track, type | Title | Authors | Link | Runs and statistics reported |
|---|---|---|---|---|---|
| 1 | GECCO 2026, CS, full paper | Social Learning Strategies for Evolved Virtual Soft Robots | Ege de Bruin, Kyrre Glette, Kai Olav Ellefsen, Giorgia Nadizar, Eric Medvet | https://arxiv.org/abs/2604.12482 (ACM DOI 10.1145/3795095.3805149) | Evolution Gym, 2D; 20 repetitions per combination (the HTML text is garbled as "2020"; the stated compute total implies 20); Mann-Whitney U with Benjamini-Hochberg correction, alpha 0.05; 200 bodies, 50 generations; code and data public |
| 2 | GECCO 2026, GA, poster | LLMigrate: Large Language Models as Migration Controllers in Island-Based Evolutionary Design of Soft Robots | Emir Buğra Şahin, Ege Demir, Bilgehan Altıntaş, Yusuf H. Şahin | official poster list | not checked |
| 3 | GECCO 2025, CS, full paper | Controller Distillation Reduces Fragile Brain-Body Co-Adaptation and Enables Migrations in MAP-Elites | Alican Mertan, Nick Cheney | https://arxiv.org/abs/2504.06523 (DOI 10.1145/3712256.3726368) | Evogym 2D, Walker-v0; "averaged over 20 repetitions"; Wilcoxon rank sum test, p = .05; 10,000 generations; code public |
| 4 | GECCO 2025, CS, poster | Accelerating Soft Robot Evolution Using N-gram-based Controller Inheritance and Genetic Co-Design | Yue Xie, Xueming Yan, Fumiya Iida | official poster list | not checked |
| 5 | GECCO 2024, EML, full paper | Towards Multi-Morphology Controllers with Diversity and Knowledge Distillation | Alican Mertan, Nick Cheney | https://arxiv.org/abs/2404.14625 (DOI 10.1145/3638529.3654013) | Evolution Gym 2D; "Unless otherwise noted, each simulation is repeated 5 times"; one-sample t-test and Wilcoxon rank sum, p = 0.05; code public |
| 6 | GECCO 2024, GECH, full paper | Lamarckian Co-design of Soft Robots via Transfer Learning | Kazuaki Harada, Hitoshi Iba | official list | not checked |
| 7 | GECCO 2024, CS, full paper | Understanding Fitness Landscapes in Morpho-Evolution via Local Optima Networks | Sarah L. Thomson, Léni K. Le Goff, Emma Hart, Edgar Buchanan | official list | not checked (robot morpho-evolution; not confirmed to be voxel-based) |
| 8 | GECCO 2024, NE, full paper | Evolving Generalist Controllers to Handle a Wide Range of Morphological Variations | Corinna Triebold, Anil Yaman | official list | not checked |
| 9 | ALIFE 2025, talk (proceedings DOI 10.1162/ISAL.a.891); extended in Artificial Life (DOI 10.1162/ARTL.a.476) | Evolutionary Brain-Body Co-Optimization Consistently Fails to Select for Morphological Potential | Alican Mertan, Nick Cheney | https://arxiv.org/abs/2508.17464 | Evogym 2D; exhaustive landscape of 1,305,840 morphologies; "In 100 independent repetitions" per algorithm (AFPO, MAP-Elites, MIP); Mann-Whitney U; code and data public (run counts read from the journal version) |
| 10 | ALIFE 2024, talk, session "Robotic systems" (Artificial Life Conference Proceedings 36) | Effective Design and Interpretation in Voxel-Based Soft Robotics: A Part Assembly Approach with Bayesian Optimization | Takumi Saito, Mizuki Oka | https://2024.alife.org/detailed_program.html | not checked |
| 11 | ALIFE 2024, talk, session "Robot Behavior Modeling" | Differentiable Soft Robot Modeling and Training with the Material Point Method | Kameron Bielawski et al. | same programme page | not checked |

Also relevant:

- Replication-framed work is accepted at GECCO: "In Search of the Ingredients of Open-Endedness: Replicating Picbreeder with Large Vision-Language Models" (Sam Earle, Kai Arulkumaran, Akarsh Kumar, Andrew Dai, Julian Togelius, Sebastian Risi), CS track, full paper, GECCO 2026; "Assessing Reproducibility in Evolutionary Computation: A Case Study using Human- and LLM-based Assessment" (Francesca Da Ros, Tarik Začiragić, Aske Plaat, Thomas Bäck, Niki van Stein), BBSR track, GECCO 2026. https://gecco-2026.sigevo.org/Accepted+Papers
- GECCO 2025 Companion, pages 2090-2098: "A Study on Morphological and Behavioral Adaptations from Multi-Task Morphoevolution by Voxel-based Soft Robots" (Ashwin V. A, Harish G. M, Jayadev D, Shunmuga Velayutham C). Seen only in a bibliographic listing (https://researchr.org/publication/AMDC25/bibtex), not on an official page; probably a workshop paper. **Unconfirmed.**
- ALIFE 2026: no individual paper could be confirmed. The proceedings (https://direct.mit.edu/isal/isal2026/volume/38) are not readable by automated tools and the programme page lists sessions only. The special session "Co-design of Robot Morphology and Control" and the "Virtual Creature Competition" workshop show the topic was present. **Unconfirmed at paper level.**
- ALIFE 2025: the programme page lists no individual papers; only item 9 was confirmed, through its arXiv record. A tutorial "Co-Design of Robot Bodies and Brains" (Kyrre Glette, Ege de Bruin) ran there. https://2025.alife.org/program

What the examples show **[inference]**:

- Every paper whose text was checked uses the 2D Evolution Gym simulator; none uses 3D voxels or MuJoCo. A validated 3D re-implementation would stand out, and reviewers are likely to ask how it relates to Evolution Gym.
- Independent runs reported: 5 (GECCO 2024, EML), 20 (GECCO 2025 CS and GECCO 2026 CS), 100 per algorithm (ALIFE 2025 paper in its journal version). Twenty runs per condition with a non-parametric test (Wilcoxon rank sum or Mann-Whitney U, with a multiple-comparison correction in the 2026 paper) matches the two most recent CS-track acceptances.
- All checked papers publish their code; the 2026 paper also has a dataset DOI.
- The same few groups account for most acceptances, and the CS track accepts 5 to 8 full papers a year.

---

## 9. Open items to re-check

1. GECCO 2027 deadline time zone (not on the official pages).
2. GECCO 2027 code-submission pilot details, supplementary size limit and submission system (announced "later").
3. GECCO 2027 registration fees and whether an "Unaffiliated" rate exists again; whether SIGEVO-only membership gives the $500 APC.
4. GECCO 2027 Hot Off the Press, LBA, workshop-paper and competition calls (not published).
5. ALIFE 2027 call for papers: deadline, page limit, single- or double-blind, hybrid or in-person (not published).
6. MIT Press (Artificial Life, Evolutionary Computation), TELO, Soft Robotics and Royal Society journal pages: open in a normal browser and confirm the items marked [excerpt only].
7. The alma mater's own affiliation policy.
8. ALIFE 2026 proceedings: look for voxel-soft-robot papers in the co-design special session.
