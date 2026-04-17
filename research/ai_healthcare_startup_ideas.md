# AI + Healthcare/Biotech Startup Ideas

**Team Profile:**
- **Person A (Pre-med, UPenn Lynch Lab):** Kristen Lynch's lab -- RNA biology, alternative splicing, immune cell regulation. Deep understanding of T cell biology, immunology, and molecular mechanisms. Access to UPenn's biomedical ecosystem (Perelman School of Medicine, Penn Institute for RNA Innovation, Penn Immunology Institute).
- **Person B (CS, UW-Madison Skala Lab):** Melissa Skala's lab -- optical metabolic imaging (OMI), fluorescence lifetime imaging microscopy (FLIM), NAD(P)H/FAD autofluorescence, label-free cell analysis, tumor organoids, CAR-T cell QC. Access to Morgridge Institute, CLIMB collaboration (UIUC), and cutting-edge multiphoton imaging hardware.
- **Person C (Recruit):** TBD -- ideally someone with business/biotech BD experience or complementary technical skills.

**Key Insight:** The Skala Lab has already spun out **SeLight LLC** (CAR-T cell QC via metabolic imaging), validating that this lab's technology has commercial legs. The Lynch Lab's expertise in immune cell regulation and alternative splicing is directly complementary -- together, this team sits at the intersection of *measuring* cell health (imaging) and *understanding* cell biology (molecular mechanisms). That's rare.

---

## Idea 1: CellSight -- AI-Powered Label-Free Cell Therapy QC Platform

### The Problem
Cell therapy manufacturing (CAR-T, stem cells, NK cells) has a massive quality control bottleneck. Current QC methods require destructive assays (flow cytometry, cytokine panels, killing assays) that consume product, take days, and only sample a fraction of the batch. Manufacturers cannot assess cell fitness in real-time during production, leading to batch failures worth $300K-$500K each and 30-40% manufacturing failure rates.

### Current Solutions & Gaps
- **Flow cytometry:** Destructive, samples only ~0.1% of batch, snapshot-only
- **SeLight LLC (Skala Lab spin-out):** Focused on pre-manufacturing T cell screening; not a full manufacturing QC platform with software + analytics
- **Cellares, Lonza, National Resilience:** Manufacturing automation, but QC is still old-school
- **Gap:** No one offers continuous, non-destructive, AI-driven QC across the entire manufacturing workflow as a software platform

### Market Size
- Cell & gene therapy manufacturing QC: **$2.8B by 2031**, $12.8B by 2033 (CAGR 15.8%)
- Cell therapy technologies overall: **$7.19B** (2023), growing to $14.22B by 2033
- Cell therapy manufacturing services: **$9.21B** in 2026

### Why This Team
- Person B has direct access to the OMI/FLIM techniques that SeLight uses -- they understand the imaging pipeline intimately and can build the software layer
- Person A understands T cell biology and immunology from the Lynch Lab -- can define what "cell fitness" means biologically for different therapy types
- They could differentiate from SeLight by being software-first (cloud analytics platform that works with any compatible imaging hardware) rather than hardware-first

### Competition
- SeLight LLC (nascent, hardware-focused, pre-manufacturing only)
- Cellares (manufacturing automation, not QC analytics)
- Fluidigm/Standard BioTools (instruments, not AI analytics)
- No pure-play AI QC analytics platform exists

### Path to Revenue
1. Partner with 2-3 CDMO/academic manufacturing sites for pilot data (free)
2. Build cloud platform that ingests OMI/FLIM data and outputs cell fitness scores
3. Charge per-batch QC analysis ($5K-$15K per batch) or annual SaaS ($100K-$500K per site)
4. Expand to stem cell, NK cell, and gene therapy QC

### YC Pitch
"We're building the AI quality control brain for cell therapy manufacturing -- replacing destructive, days-long assays with real-time, label-free imaging analytics that predict batch success before you waste $500K."

---

## Idea 2: SpliceRx -- AI Platform for RNA Splicing-Based Drug Target Discovery

### The Problem
~95% of human genes undergo alternative splicing, and aberrant splicing drives thousands of diseases (cancer, neurodegeneration, autoimmune). Yet most drug discovery still targets single protein isoforms, ignoring the splicing landscape entirely. Identifying which splice variants are disease-driving vs. bystanders requires deep expertise that most pharma teams lack.

### Current Solutions & Gaps
- **Traditional target discovery:** Focuses on protein/gene level, misses splice-variant-specific targets
- **Existing RNA therapeutics (Ionis, Stoke Therapeutics):** Focus on specific ASOs/splice-switching oligos but don't offer a platform for systematic target ID
- **AI drug discovery (Recursion, Insilico):** Focus on small molecules and protein targets, not splicing biology
- **Gap:** No AI platform systematically mines transcriptomic data to identify disease-driving splice variants and match them to therapeutic modalities

### Market Size
- AI drug discovery: **$3-5B** in 2026, projected $10-13B by 2031-2033
- RNA therapeutics: **$8.5B** in 2025, growing rapidly
- Drug target discovery services: multi-billion dollar market within pharma R&D spend ($250B+ annually)

### Why This Team
- Person A is literally in the lab that pioneered understanding of signal-responsive alternative splicing in immune cells -- they have domain expertise that would take competitors years to build
- Person B can build the ML pipeline: foundation models trained on RNA-seq data to predict disease-relevant splice events
- Access to UPenn's RNA Innovation Institute and the broader Penn immunology ecosystem for validation

### Competition
- Envisagenics (AI splice-variant analysis, raised ~$20M) -- closest competitor but focused on oncology
- SpliceCore / Remix Therapeutics (splice-modulating therapeutics, not a discovery platform)
- Deep Genomics (acquired by Illumina) -- broader RNA, not splice-focused
- Stoke Therapeutics (splice-switching therapeutics, not a platform)

### Path to Revenue
1. Build MVP: AI model trained on public RNA-seq datasets (TCGA, GTEx, ENCODE) to rank disease-associated splice variants
2. Offer as SaaS to pharma/biotech R&D teams ($50K-$200K annual license)
3. Co-development deals: partner with pharma on specific targets for milestones + royalties
4. Internal pipeline: use platform to identify and patent novel splice-variant drug targets

### YC Pitch
"95% of human genes are alternatively spliced, but drug discovery ignores splicing. We built an AI platform that finds disease-driving splice variants and matches them to therapeutics -- unlocking an entirely new class of drug targets."

---

## Idea 3: MetaboPath -- AI Microscopy Analysis Platform for Research Labs

### The Problem
Research labs worldwide generate terabytes of microscopy data (fluorescence, confocal, multiphoton, FLIM) but analyze it with manual, irreproducible workflows. A postdoc might spend 40% of their time on image segmentation, feature extraction, and quantification. Results vary between analysts, making studies hard to reproduce. Label-free imaging techniques (OMI, FLIM, autofluorescence) are growing rapidly but have especially poor tooling -- most existing software was designed for fluorescent labels.

### Current Solutions & Gaps
- **ImageJ/FIJI:** Free, powerful, but requires scripting expertise and is not cloud-native
- **CellProfiler:** Open-source, good for high-content screening, steep learning curve
- **ZEISS arivis, Imaris, Aivia:** Expensive ($10K-$50K/year), tied to specific hardware, not AI-native
- **Aiforia:** Cloud-based AI pathology, but focused on clinical H&E/IHC, not research imaging
- **Gap:** No cloud-native, AI-first analysis platform purpose-built for label-free and metabolic imaging modalities (FLIM, OMI, autofluorescence, Raman)

### Market Size
- AI in microscopy: **$1.32B** in 2026, growing to $4.6-9.8B by 2033-2035
- Life science software: **$20.8B** (2024), projected $70B by 2034
- Cloud SaaS segment growing at 8.2% CAGR, but AI-native tools growing much faster

### Why This Team
- Person B works daily with OMI/FLIM data in the Skala Lab and knows exactly what's broken in the analysis pipeline
- Person A brings biological context -- understanding what the imaging data means for cell biology
- Access to real research data from two world-class labs for training and validation
- CLIMB collaboration gives access to an even broader set of label-free imaging modalities

### Competition
- Aiforia (cloud AI pathology -- clinical, not research label-free)
- ZEISS arivis (enterprise, hardware-tied, not AI-native)
- Napari (open-source viewer, no AI built in)
- ~80 digital pathology companies, but almost none serve research-grade label-free imaging

### Path to Revenue
1. Build free tier for academic labs (cloud upload + basic AI segmentation for FLIM/OMI data)
2. Pro tier ($200-$500/month per lab) with advanced quantification, batch processing, export
3. Enterprise tier for pharma/biotech imaging cores ($20K-$100K/year)
4. Marketplace for custom analysis modules (community + paid plugins)

### YC Pitch
"We're Figma for microscopy -- a cloud-native AI platform that turns raw label-free imaging data into publication-ready quantification in minutes instead of weeks, starting with the fastest-growing modalities in biology."

---

## Idea 4: ImmunoMetric -- Predicting Immunotherapy Response via Metabolic Imaging + RNA Signatures

### The Problem
Only 20-40% of cancer patients respond to immunotherapy (checkpoint inhibitors like Keytruda/Opdivo), but there's no reliable way to predict who will respond before starting treatment. Patients endure months of toxic, expensive therapy ($150K-$250K/year) before learning it doesn't work. Current biomarkers (PD-L1 expression, tumor mutational burden) are imprecise and miss the metabolic state of the tumor microenvironment.

### Current Solutions & Gaps
- **PD-L1 IHC staining:** Standard of care, but only ~30% predictive accuracy
- **TMB (Tumor Mutational Burden):** Requires sequencing, moderate predictive value
- **Tempus, Foundation Medicine:** Genomic profiling, but miss metabolic/functional state
- **Gap:** No one combines metabolic imaging (real-time functional state of tumor + immune cells) with transcriptomic splicing signatures to predict response

### Market Size
- Immunotherapy market: **$120B+** by 2030
- Companion diagnostics: **$7.5B** in 2026, growing to $15B+ by 2032
- Precision oncology diagnostics: **$12B+** by 2030
- AI in oncology: multi-billion dollar segment

### Why This Team
- Person B can build the metabolic imaging analysis pipeline (redox ratio, FLIM features from tumor biopsies/organoids)
- Person A understands the immunology -- specifically how alternative splicing in T cells affects their anti-tumor function (Lynch Lab's core expertise)
- Combined signature (metabolic imaging features + splice-variant RNA markers) would be a novel, multi-modal biomarker that neither genomics-only nor imaging-only companies can replicate

### Competition
- Tempus AI ($6B+ valuation) -- genomics-focused, no metabolic imaging
- Foundation Medicine (Roche) -- genomic profiling
- PathAI -- computational pathology from H&E, not metabolic imaging
- No one combines OMI + splicing signatures

### Path to Revenue
1. Retrospective study: analyze existing tumor organoid imaging data (Skala Lab) + RNA-seq data to build predictive model
2. Partner with 2-3 oncology clinics for prospective validation
3. License as LDT (lab-developed test) initially -- faster to market than FDA-cleared IVD
4. Per-test reimbursement ($3K-$8K per test, similar to Foundation Medicine)

### YC Pitch
"We predict which cancer patients will respond to immunotherapy before treatment starts by combining metabolic imaging with RNA splicing signatures -- a multimodal biomarker that's 2x more accurate than current methods."

---

## Idea 5: OrganoScreen -- AI-Powered Patient-Derived Organoid Drug Screening Platform

### The Problem
Patient-derived organoids (PDOs) are the most promising model for personalized drug testing, but the analysis bottleneck is brutal. Growing organoids is getting easier; interpreting their response to drugs is not. Labs manually score organoid viability, morphology, and drug response -- a process that's slow, subjective, and doesn't scale. Label-free imaging can capture drug response without killing the organoids, but the analysis software doesn't exist.

### Current Solutions & Gaps
- **Manual scoring:** Subjective, slow, doesn't scale
- **CellTiter-Glo / ATP assays:** Destructive endpoint assays, lose the organoid
- **High-content screening (Molecular Devices, PerkinElmer):** Expensive instruments, designed for 2D, poor at 3D organoid analysis
- **Rosebud Biosciences, HeartBeat.bio:** Organoid screening companies, but proprietary pipelines, not a platform
- **Gap:** No AI software platform that takes label-free imaging of organoids and automatically quantifies drug response over time

### Market Size
- Organoid market: **$3B** (2023), projected **$15B** by 2031
- Preclinical CRO market: **$7-11B** in 2026
- Drug screening services: multi-billion dollar segment
- 102+ organoid startups globally, all needing analysis tools

### Why This Team
- Person B works with tumor organoid imaging data daily in the Skala Lab -- this is literally the lab's bread and butter
- Person A understands the biology of drug response at the molecular level
- The Skala Lab has published extensively on metabolic imaging of organoid drug response (head and neck cancer, neuroendocrine tumors)

### Competition
- Molecular Devices (hardware + basic software, not AI-native for organoids)
- PHIO Scientific (AI organoid screening, early stage)
- CellVoyager (Yokogawa) -- high-content, not label-free native
- No dedicated AI platform for label-free organoid drug response quantification

### Path to Revenue
1. Build cloud platform: upload organoid time-lapse imaging data, get automated drug response curves
2. Free tier for academic labs, paid tier ($300-$1K/month) for pharma/CROs
3. Per-screen analysis for CROs ($500-$2K per drug panel)
4. Data moat: aggregate anonymized drug-organoid response data to build predictive models

### YC Pitch
"We're the analytics layer for the $15B organoid market -- AI that turns label-free organoid imaging into automated drug response scores, replacing subjective manual analysis with reproducible, quantitative results."

---

## Idea 6: TxPredict -- AI Platform for Predicting Cell Therapy Manufacturing Outcomes

### The Problem
Cell therapy manufacturing has a ~30-40% batch failure rate, and manufacturers don't know a batch will fail until the end of a 9-14 day process (costing $300K-$500K per failure). The starting material (patient's T cells / donor cells) varies wildly in quality, and there's no way to predict at Day 0 whether a batch will succeed. Post-manufacturing potency assays take additional days and are destructive.

### Current Solutions & Gaps
- **Flow cytometry panels:** Standard QC, but snapshot-only and destructive
- **Potency assays (killing assays, cytokine release):** Take 3-7 days, destructive
- **SeLight LLC:** Pre-manufacturing screening via metabolic imaging (early stage, hardware focus)
- **Process analytics (Lonza, Cytiva):** Monitor bioreactor parameters, not cell-level quality
- **Gap:** No predictive analytics platform that combines Day 0 cell characterization with process data to predict manufacturing success/failure in real-time

### Market Size
- Cell & gene therapy manufacturing QC: **$2.8B** by 2031, $12.8B by 2033
- Cell therapy manufacturing services: **$9.21B** in 2026
- Each prevented batch failure saves $300K-$500K -- massive ROI story

### Why This Team
- Person B understands metabolic imaging of T cells (Skala Lab has published on this for CAR-T specifically)
- Person A understands T cell biology and what makes a "fit" T cell from the Lynch Lab's work on immune cell regulation
- Combined: they can define the biological features that predict manufacturing success AND build the AI to detect them

### Competition
- SeLight LLC (pre-manufacturing only, hardware-focused)
- Cellares (manufacturing automation, not predictive analytics)
- Ori Biotech (manufacturing platform, not predictive QC)
- No pure-play predictive analytics for cell therapy manufacturing

### Path to Revenue
1. Partner with 1-2 academic cell therapy manufacturing centers for retrospective data
2. Build predictive model: Day 0 cell features --> manufacturing outcome
3. SaaS platform ($50K-$200K/year per manufacturing site)
4. Per-batch prediction service ($2K-$5K per batch)
5. Expand: failure root-cause analysis, process optimization recommendations

### YC Pitch
"Cell therapy batches fail 30-40% of the time at $500K each. We predict which batches will fail before manufacturing starts -- saving CDMOs millions and getting therapies to patients faster."

---

## Idea 7: SpectraPath -- AI-Powered Label-Free Digital Pathology for Underserved Markets

### The Problem
There's a global shortage of pathologists (estimated 50,000+ deficit worldwide), and it's worst in low- and middle-income countries where cancer diagnosis is most delayed. Traditional digital pathology requires expensive H&E staining, slide scanners ($200K+), and AI trained on stained images. But label-free imaging techniques (autofluorescence, quantitative phase imaging) can extract diagnostic information from unstained tissue -- cheaper, faster, no reagents needed.

### Current Solutions & Gaps
- **PathAI, Paige, Aiforia:** AI pathology on stained slides -- requires expensive prep, staining, scanning
- **Mecha Health (YC):** AI for radiology, not pathology
- **Label-free pathology research:** Published in journals (Nature BME, etc.) but no commercial product
- **Gap:** No company has commercialized AI pathology on unstained/label-free tissue images, which would dramatically reduce cost and turnaround

### Market Size
- Digital pathology: **$1.3-2.0B** in 2025-2026, growing to $2.76B by 2035
- AI in pathology: **$107M** (2025) to $347M by 2030 (CAGR 26.5%)
- But the real TAM is the $20B+ pathology services market that's currently inaccessible to AI because of cost/infrastructure barriers
- Global pathology workforce gap = massive unmet demand

### Why This Team
- Person B has expertise in label-free imaging modalities and AI analysis from the Skala Lab
- Person A understands the clinical pathology workflow and what pathologists need to see
- CLIMB collaboration provides access to multiple label-free imaging modalities (QPI, FLIM, SHG, autofluorescence)
- First-mover advantage in a space where the research exists but no one has productized it

### Competition
- ~80 digital pathology AI companies, but ALL require stained tissue
- Proscia (platform, stained slides)
- Ibex Medical (AI diagnosis, stained slides)
- No commercial label-free pathology AI product exists

### Path to Revenue
1. Start with one high-value use case: rapid intraoperative margin assessment (unstained frozen sections)
2. Partner with 2-3 hospitals for validation
3. LDT pathway initially, then 510(k) clearance
4. Per-slide analysis fee ($20-$50) or annual site license ($100K-$500K)
5. Expand to LMIC markets where staining infrastructure doesn't exist

### YC Pitch
"We're building AI pathology that works on unstained tissue -- no staining, no expensive scanners, no reagents. It's 10x cheaper and 10x faster than existing digital pathology, and it works where pathologists don't exist."

---

## Idea 8: ImmunoSplice -- AI Companion Diagnostic for Autoimmune Disease Treatment Selection

### The Problem
Autoimmune diseases (RA, lupus, MS, IBD, psoriasis) affect 50M+ Americans and treatment is trial-and-error. Patients cycle through 3-5 biologics ($30K-$80K/year each) over 2-3 years before finding one that works. There's no diagnostic to predict which biologic will work for which patient. The underlying biology is clear -- alternative splicing of immune genes determines how T cells and B cells respond to therapy -- but no one has turned this into a diagnostic.

### Current Solutions & Gaps
- **Trial-and-error prescribing:** Current standard, wastes years and hundreds of thousands of dollars
- **Genomic tests (23andMe, HLA typing):** Static genetic risk, don't predict treatment response
- **Progenity, Scipher Medicine:** Some biomarker work, but limited to specific diseases/drugs
- **Gap:** No multi-disease platform that uses splicing-based biomarkers + functional immune profiling to predict biologic treatment response

### Market Size
- Autoimmune therapeutics: **$150B+** market globally
- Companion diagnostics: **$7.5B** in 2026, growing to $15B+
- Autoimmune diagnostics specifically: **$5B+** and growing
- 50M+ US patients, most cycling through multiple expensive biologics

### Why This Team
- Person A's lab (Lynch Lab) literally studies how alternative splicing controls immune cell function in response to stimulation -- this IS the biology underlying treatment response
- Person B can build the computational pipeline (ML on RNA-seq + imaging data)
- UPenn's immunology ecosystem is world-class for clinical validation

### Competition
- Scipher Medicine (anti-TNF response prediction, single disease) -- closest but narrow
- Progenity (GI-focused diagnostics)
- PredictImmune (IBD prognosis, UK-based)
- No multi-disease, splice-based treatment response platform

### Path to Revenue
1. Start with one disease + one drug class (e.g., RA + anti-TNF biologics) using public datasets + Lynch Lab biological expertise
2. Validate retrospectively on clinical cohorts (UPenn partnerships)
3. LDT launch: $2K-$5K per test, reimbursable
4. Expand to lupus, IBD, MS, psoriasis -- same platform, different models
5. Pharma partnerships: drug companies pay for companion diagnostic development

### YC Pitch
"Autoimmune patients waste 2-3 years and $200K cycling through biologics that don't work. We built an AI diagnostic using RNA splicing signatures to predict which treatment will work on the first try."

---

## Idea 9: NeuroSight -- Non-Invasive Neonatal Brain Monitoring AI Platform

### The Problem
Brain injury in neonates (especially those with congenital heart disease undergoing cardiac surgery) is a major cause of lifelong disability. Current monitoring (EEG, NIRS) provides limited, noisy data that clinicians struggle to interpret in real-time. Optimal cerebral oxygen delivery during surgery is critical but poorly monitored. There's no AI system that synthesizes multi-modal neuromonitoring data into actionable clinical guidance.

### Current Solutions & Gaps
- **Standard NIRS (Medtronic, Edwards):** Single-parameter (rSO2), noisy, no AI interpretation
- **EEG monitoring:** Requires specialized technicians, hard to interpret in real-time during surgery
- **Lynch Lab (CHOP):** Jennifer Lynch's lab is developing advanced optical neuromonitoring but it's research-stage
- **Gap:** No AI platform that fuses multi-modal neuromonitoring data (optical, EEG, vitals) and provides real-time clinical decision support for neonatal brain protection

### Market Size
- Neonatal monitoring devices: **$1.5B+** globally
- Cerebral oximetry: **$500M+** and growing
- AI clinical decision support: **$12.5B** by 2026
- Pediatric cardiac surgery: ~40,000 cases/year in US alone
- Broader: all NICU patients (~500,000/year in US)

### Why This Team
- UPenn/CHOP connection (the biomedical optics lab at CHOP doing this research is UPenn-affiliated)
- Person A (pre-med at UPenn) could potentially access this ecosystem
- Person B (CS) builds the AI layer that makes raw optical data clinically actionable
- Cross-pollination: metabolic imaging expertise (Skala Lab) applied to cerebral monitoring data

### Competition
- Medtronic INVOS (basic NIRS, no AI)
- Edwards (cerebral oximetry, no AI)
- Masimo (pulse oximetry, expanding to neuro)
- No AI-native neonatal neuromonitoring platform

### Path to Revenue
1. Build AI model on retrospective NIRS + outcome data (CHOP has extensive datasets)
2. Software overlay for existing NIRS hardware (510(k) pathway as clinical decision support)
3. Per-procedure license ($500-$1K) or annual hospital site license ($50K-$200K)
4. Expand beyond cardiac surgery to all NICU monitoring

### YC Pitch
"Brain injury during neonatal heart surgery causes lifelong disability. We built an AI system that monitors cerebral oxygen delivery in real-time and tells surgeons exactly when to intervene -- turning noisy sensor data into actionable guidance."

---

## Summary Comparison Table

| # | Idea | TAM | Time to MVP | Regulatory | Moat | Lab Leverage |
|---|------|-----|-------------|------------|------|-------------|
| 1 | CellSight (Cell Therapy QC) | $12.8B by 2033 | 6-9 months | Low (research tool) | Data + domain | Skala +++, Lynch ++ |
| 2 | SpliceRx (Splicing Drug Targets) | $10B+ | 6-8 months | None (SaaS) | IP + data | Lynch +++, Skala + |
| 3 | MetaboPath (Microscopy AI) | $4.6-9.8B by 2033 | 4-6 months | None (SaaS) | Network + data | Skala +++, Lynch + |
| 4 | ImmunoMetric (Immunotherapy Dx) | $15B+ CDx | 9-12 months | Medium (LDT) | Multi-modal IP | Both +++ |
| 5 | OrganoScreen (Organoid Analysis) | $15B by 2031 | 5-8 months | Low (research tool) | Data + domain | Skala +++, Lynch ++ |
| 6 | TxPredict (Manufacturing Prediction) | $12.8B by 2033 | 6-9 months | Low (research tool) | Data + domain | Both +++ |
| 7 | SpectraPath (Label-Free Pathology) | $20B+ services | 9-12 months | Medium-High (FDA) | First-mover + IP | Skala +++, Lynch ++ |
| 8 | ImmunoSplice (Autoimmune CDx) | $15B+ CDx | 8-12 months | Medium (LDT) | Biology IP | Lynch +++, Skala + |
| 9 | NeuroSight (Neonatal Brain AI) | $1.5B+ | 9-12 months | Medium (510k) | Clinical data | Medium (CHOP link) |

## Top Recommendations (Ranked)

### Tier 1 -- Strongest fit for this team, fastest to market, largest opportunity:
1. **MetaboPath (#3)** -- Lowest regulatory burden, fastest MVP, massive market, directly uses daily Skala Lab expertise, clear PLG growth model. Think "the Weights & Biases of microscopy."
2. **OrganoScreen (#5)** -- Skala Lab literally does this research. Organoid market is exploding. 102+ organoid startups all need analysis tools. Picks-and-shovels play.
3. **CellSight (#1)** -- Differentiates from SeLight by being software-first. Massive pain point. Clear ROI story ($500K saved per prevented failure).

### Tier 2 -- High potential but longer timeline or higher complexity:
4. **SpliceRx (#2)** -- Uniquely leverages Lynch Lab expertise. Huge pharma demand for novel targets. But longer sales cycles (pharma partnerships).
5. **ImmunoSplice (#8)** -- Enormous patient impact. Lynch Lab is literally the world expert on this biology. But regulatory + clinical validation takes time.
6. **TxPredict (#6)** -- Combines both labs perfectly. Strong ROI story. But needs manufacturing partner data access.

### Tier 3 -- High TAM but harder execution for student team:
7. **ImmunoMetric (#4)** -- Most ambitious, biggest moat if it works. But clinical validation timeline is long.
8. **SpectraPath (#7)** -- First-mover in label-free pathology is compelling, but FDA pathway is complex.
9. **NeuroSight (#9)** -- Smaller TAM, weaker direct lab connection, more hardware-dependent.

---

## Sources

- [Skala Lab - Morgridge Institute](https://morgridge.org/research/labs/skala/)
- [Lynch Lab - UPenn](http://www.kwlynchlab.org/)
- [CLIMB - Center for Label-free Imaging](https://climb.illinois.edu/)
- [SeLight LLC - CLIMB News](https://climb.illinois.edu/news/78249)
- [Cell & Gene Therapy Manufacturing QC Market](https://www.europeanpharmaceuticalreview.com/news/186228/cell-and-gene-therapy-manufacturing-qc-market-to-value-2-8-billion-by-2031/)
- [AI in Microscopy Market](https://www.towardshealthcare.com/insights/ai-in-microscopy-market-sizing)
- [AI Drug Discovery Market](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-drug-discovery-market)
- [AI in Clinical Trials Market](https://www.fortunebusinessinsights.com/ai-in-clinical-trials-market-114081)
- [Digital Pathology Market](https://www.precedenceresearch.com/digital-pathology-market)
- [AI in Ophthalmology Market](https://www.towardshealthcare.com/insights/ai-in-ophthalmology-market-sizing)
- [Organoid Research Models - Tracxn](https://tracxn.com/d/trending-business-models/startups-in-organoid-research-models/__XSqxeWBKMxm3FAh6miORkadprmLT2WXcpfv2Fh3Tfsk/companies)
- [AI Healthcare Investment Trends](https://qubit.capital/blog/ai-healthcare-investment-trends)
- [YC Healthcare Startups](https://www.ycombinator.com/companies/industry/healthcare)
- [Life Science Software Market](https://www.towardshealthcare.com/insights/life-science-software-market-sizing)
- [Companion Diagnostics Market](https://www.marketsandmarkets.com/Market-Reports/ai-remote-patient-monitoring-rpm.asp)
- [Label-free Metabolic Imaging for CAR-T - Nature BME](https://www.nature.com/articles/s41551-025-01504-7)
- [Optical Metabolic Imaging Cell-Cycle - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5680147/)
- [AI-Driven Label-Free Cell Viability - BioPharm International](https://www.biopharminternational.com/view/ai-driven-label-free-quantification-of-cell-viability-using-live-cell-analysis)
- [Mecha Health - YC](https://www.ycombinator.com/companies/industry/healthcare)
- [AI in Wound Care Market](https://www.globenewswire.com/news-release/2026/02/04/3232217/0/en/AI-in-Wound-Care-Market-Projected-to-Achieve-a-35-03-CAGR-Expanding-from-USD-0-64-Billion-to-USD-12-9-Billion-by-2034.html)
