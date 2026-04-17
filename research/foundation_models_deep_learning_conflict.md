# Foundation Models & Deep Learning for Conflict Prediction
## Comprehensive Research Review (March 2026)

---

## 1. Geospatial Foundation Models

### Prithvi-EO-2.0 (NASA/IBM)
- **Architecture:** Vision Transformer (ViT) with Masked Autoencoder (MAE) pretraining. Uses 3D patch embeddings and 3D positional embeddings for spatiotemporal inputs (sequence of T images of size H x W).
- **Parameters:** 600M (6x larger than Prithvi-EO-1.0). Also released a 300M variant.
- **Training data:** 4.2M global time series samples from NASA's Harmonized Landsat and Sentinel-2 (HLS) dataset at 30m resolution. ~7 years of multispectral imagery, covering 800+ ecoregions.
- **Training compute:** Trained on JUWELS HPC at Julich Supercomputing Centre.
- **Capabilities:** Flood detection, wildfire scar detection, land cover classification, change detection, semantic segmentation. Outperforms Prithvi-EO-1.0 by 8% across tasks and beats 6 other GFMs.
- **Open source:** Yes. Apache-2.0 license on Hugging Face (`ibm-nasa-geospatial/Prithvi-EO-2.0-600M`). Fine-tuning via `terratorch` toolkit.
- **Fine-tuning:** LoRA performs on par with full fine-tuning. Supports downstream tasks via terratorch.
- **Released:** December 4, 2024. arXiv: 2412.02732.
- **Weather variant:** Prithvi-WxC has 320M params (220M encoder + 100M decoder), hierarchical 2D ViT for weather/climate.
- **Relevance to Sentinel:** Could fine-tune for conflict-related change detection (building damage, vegetation burn scars, infrastructure destruction) using HLS imagery over the Levant.

### Clay Foundation Model (v1.5)
- **Architecture:** Two-stage transformer: (1) meta-learner to standardize multi-sensor input data, (2) standard ViT trained via MAE self-supervised learning. Parameterizes input extensively for maximum flexibility.
- **Parameters:** 632M total (encoder + decoder + optimizer states, ~1.25 GB checkpoint).
- **Training data:** 33.8 TB of imagery, ~70M chips. Sensors: Sentinel-1, Sentinel-2, Landsat 8/9, NAIP, LINZ, MODIS.
- **Training compute:** 6,400 GPU hours on H100s.
- **Embedding dimensions:** 768-dimensional output embeddings (internal encoder dim 1024, 24 layers, 16 heads).
- **Capabilities:** Semantic embeddings for similarity search, fine-tunable for classification (flood detection, deforestation), regression (carbon stock, crop yields), and generative tasks (RGB from SAR).
- **Open source:** Yes. Apache license. Code on GitHub (`Clay-foundation/model`), weights on Hugging Face (`made-with-clay/Clay`).
- **Fine-tuning:** LoRA performs on par with or better than full fine-tuning per recent PEFT research (arXiv: 2504.17397).
- **Relevance to Sentinel:** Multi-sensor support (S1+S2+Landsat) makes it ideal for fusing SAR coherence + optical change detection. Could generate per-hex embeddings as features.

### SatCLIP (Microsoft)
- **Architecture:** Contrastive learning between image encoder (CNN or ViT-16) and location encoder (Siren + Spherical Harmonics). Projects both into shared d-dimensional latent space.
- **Training data:** S2-100K dataset -- 100K multi-spectral Sentinel-2 images sampled ~uniformly over landmass (Jan 2021 - May 2023, cloud-free).
- **Capabilities:** General-purpose location embeddings. Improves prediction on 9 diverse location-dependent tasks (temperature, population density, animal recognition). Spatial smoothness controlled by hyperparameter L.
- **Open source:** Yes. GitHub `microsoft/satclip`, Hugging Face `microsoft/SatCLIP-ViT16-L40`.
- **Published:** AAAI 2025. arXiv: 2311.17179.
- **Relevance to Sentinel:** Could replace raw lat/lon with learned location embeddings as features for the GNN. Encodes "what kind of place is this" from satellite imagery -- urbanization, terrain, land use.

### GeoCLIP
- **Architecture:** CLIP-based image encoder (ViT-B/16) + location encoder (Fourier feature mapping of lat/lon capturing multi-scale spatial patterns). Contrastive loss between image and GPS features.
- **Training data:** 1.2M image-location pairs from YFCC100M dataset, globally sampled.
- **Performance:** 52.1% accuracy at region level (200km), 21.5% at city level (25km) for geolocalization.
- **Published:** NeurIPS 2023.
- **Relevance to Sentinel:** Similar to SatCLIP but trained on ground-level + overhead imagery. Location encoder could provide spatial priors for the conflict model.

### SkySense
- **Architecture:** Factorized multi-modal spatiotemporal encoder. Takes temporal sequences of optical (HSROI, TMsI) and SAR data. Pre-trained via Multi-Granularity Contrastive Learning across modalities and spatial scales. Modular design -- modules can be used individually or combined.
- **Parameters:** 2.06 billion (largest MM-RSFM to date as of CVPR 2024).
- **Training data:** 21.5M remote sensing image temporal sequences (high-res optical, medium-res temporal multispectral, temporal SAR).
- **Performance:** Evaluated on 16 datasets over 7 tasks. Outperforms GFM by 2.76%, SatLas by 3.67%, Scale-MAE by 3.61% on average.
- **Published:** CVPR 2024. GitHub: `Jack-bo1220/SkySense`.
- **SkySense V2:** Published in Nature Machine Intelligence 2025, further advances the architecture.
- **Relevance to Sentinel:** Best multi-modal RS foundation model. Could extract combined optical+SAR features per hex. BUT: 2B params means significant compute for fine-tuning.

### SpectralGPT
- **Architecture:** 3D Generative Pretrained Transformer operating in 3D space (spatial + spectral). Accommodates varying input sizes, resolutions, time series, and regions via progressive training.
- **Parameters:** 600M+, trained on 1M spectral RS images.
- **Capabilities:** 3D token generation for spatial-spectral coupling, multi-target reconstruction. Evaluated on scene classification (single/multi-label), semantic segmentation, change detection.
- **Published:** IEEE TPAMI 2024. arXiv: 2311.07113.
- **Relevance to Sentinel:** Purpose-built for spectral data. Could extract richer features from multispectral Sentinel-2 bands than standard ViT approaches.

### SatMAE
- **Architecture:** ViT with Masked Autoencoder pretraining, extended for temporal and multi-spectral satellite imagery. Uses temporal embeddings + independent masking across time steps. Groups spectral bands with distinct spectral positional encodings.
- **Performance:** +7% over SOTA on benchmark datasets, +14% transfer learning on land cover classification.
- **Published:** NeurIPS 2022. arXiv: 2207.08051.
- **Relevance to Sentinel:** Temporal masking approach directly applicable to Sentinel time-series analysis for conflict zones.

### CROMA
- **Architecture:** Contrastive Radar-Optical Masked Autoencoder. Separately encodes masked multispectral optical (Sentinel-2, 12 channels) and SAR (Sentinel-1, 2 channels), aligned in space and time. Cross-modal contrastive learning + joint fusion encoder + lightweight decoder. Introduces X-ALiBi and 2D-ALiBi for spatial bias in attention.
- **Performance:** Outperforms SOTA on classification (+1.8% finetuning, +2.4% linear, +3.5% kNN), segmentation (+6.4%). Can extrapolate to images 17.6x larger at test time.
- **Published:** NeurIPS 2023. arXiv: 2311.00566. GitHub: `antofuller/CROMA`.
- **Relevance to Sentinel:** Directly fuses S1+S2 data. Spatial ALiBi could help with varying hex sizes. Strong candidate for pre-extracting radar-optical embeddings.

### RingMo (Chinese Academy of Sciences)
- **Architecture:** V3.0 uses heat conduction-based architecture. Unified transformer encoder reconstructing masked multimodal EO data. Handles visible light, SAR, thermal infrared, multispectral.
- **Parameters:** 10 billion+ (v3.0, September 2024). World's first 10B parameter RS model.
- **Training:** 10M data samples. Training speed 2.4x faster with 1/3 the GPUs vs previous version.
- **Capabilities:** Cross-sensor interpretation, aircraft/drone imagery.
- **Relevance to Sentinel:** Massive but likely not openly available for fine-tuning. Demonstrates the scale frontier.

### Google AlphaEarth Foundations
- **Released:** April 2025. Trained on large corpus of high-resolution overhead imagery paired with text descriptions.
- **Capabilities:** Integrates Earth observation data with language and contextual data (topography, hydrology, field reports, emergency calls). Geospatial reasoning.
- **Architecture:** Cross-modal reasoning with LLMs like Gemini. Currently generating annual embeddings.
- **Relevance to Sentinel:** The text+satellite integration pattern is exactly what Sentinel needs. If made available, could provide pre-computed embeddings with contextual understanding.

---

## 2. NLP for Conflict

### Mueller & Rauh: Text-to-Onset
- **Method:** Latent Dirichlet Allocation (LDA) on 3.8M newspaper articles (1975-2015, 185 countries) -> topic features -> Random Forest classifier.
- **Key insight:** Within-country topic variation over time predicts conflict onset, even in previously peaceful countries. Text is most valuable for "hard cases" where historical indicators fail.
- **Performance (onset AUC):**
  - Text only: 0.83 [0.82, 0.85]
  - History only: 0.92 [0.91, 0.93]
  - Text + History: 0.92 [0.91, 0.92]
- **Operational system:** [conflictforecast.org](https://conflictforecast.org) -- global live forecasts.
- **Published:** Journal of the European Economic Association (JEEA).
- **Relevance to Sentinel:** Validates that NLP adds signal beyond historical conflict lags, especially for onset prediction. Text AUC of 0.83 standalone is strong. Their "within-country topic variation" concept maps directly to GDELT topic tracking per hex.

### AraBERT
- **Architecture:** BERT-based, pretrained specifically for Arabic.
- **Training data:** Arabic text corpus (details in arXiv: 2003.00104).
- **Performance:** SOTA on most Arabic NLP tasks. Outperforms mBERT on 84% of compared tasks (42/50 models). Up to 99% F1 on Arabic text multi-class categorization.
- **Variants:** AraBERTv2, AraBERT-large, AraBERT-Twitter.
- **Open source:** Yes. GitHub: `aub-mind/arabert`.
- **Relevance to Sentinel:** Primary candidate for encoding Arabic GDELT article text, ACLED notes, and Telegram content for the Levant region.

### AlephBERT (Hebrew)
- **Architecture:** BERT-based, pretrained for Modern Hebrew.
- **Training data:** 17.9GB corpus (OSCAR + Wikipedia + Twitter). Vocabulary: 52K tokens.
- **Performance:** SOTA on Hebrew segmentation, POS tagging, morphological tagging, NER, sentiment analysis.
- **Published:** arXiv: 2104.04052.
- **HeRo (newer):** RoBERTa and Longformer Hebrew models (arXiv: 2304.11077).
- **Relevance to Sentinel:** For encoding Hebrew-language social media and news about northern Israel conflict dynamics.

### CAMeL Tools (NYU Abu Dhabi)
- **Toolkit:** Open-source Python toolkit for Arabic NLP. Morphological analysis, dialect identification, NER, sentiment analysis.
- **CAMeLBERT:** Collection of BERT models for MSA, dialectal Arabic, classical Arabic, and mixed.
- **Collaboration:** With AUB (Beirut) and Qatar University on Arabic sentiment analysis.
- **Relevance to Sentinel:** Preprocessing pipeline for Arabic text before embedding. Dialect identification critical for Lebanese Arabic vs MSA news.

### XLM-R
- **Architecture:** Transformer, pretrained on 100 languages, 2TB+ data.
- **Performance:** SOTA on cross-lingual classification, sequence labeling, QA. Outperforms other cross-lingual approaches by 3%+ in zero-shot sentiment. However, lower individual performance on Arabic and Hebrew vs English/German.
- **Relevance to Sentinel:** Backup option if AraBERT/AlephBERT fail on cross-lingual transfer tasks. Good for zero-shot classification of mixed-language Levant content.

### SONAR (Meta)
- **Architecture:** Single text encoder covering 200 languages, multilingual and multimodal fixed-size sentence embeddings.
- **Performance:** Substantially outperforms LASER3 and LabSE on xsim and xsim++ multilingual similarity search.
- **Relevance to Sentinel:** Best option for unified Arabic+Hebrew+English embedding space. Could embed all GDELT/news text into same space regardless of language.

### Multilingual Sentence Transformers
- **For Arabic:** distilbert-base-multilingual-cased works well with limited compute. SBERT multilingual models support 15+ languages including Arabic.
- **Dimensionality reduction:** PCA and IPCA effectively reduce embedding dimensions while preserving performance. PCA from 768d to 32d is feasible.
- **Relevance to Sentinel:** Plan for text_encoder.py (sentence-transformers -> 32-dim PCA) is well-validated by research.

---

## 3. GNNs for Conflict/Crisis

### HydraNet (VIEWS, arXiv: 2506.14817, June 2025)
- **Architecture:** Monte Carlo Dropout LSTM U-Net. CNN convolutional layers for spatial dependencies on 2D grids + encoder-decoder with skip connections + LSTM for temporal dynamics.
- **Task:** Forecasts 3 types of violence (state-based, non-state, one-sided) at subnational (PRIO-GRID month) level, up to 36 months ahead.
- **Output:** Joint classification + regression. Probabilistic estimates AND expected magnitudes.
- **Uncertainty:** MC Dropout with 128 posterior samples per prediction. Approximate Bayesian predictive posterior.
- **Performance:** SOTA across all tasks.
- **Relevance to Sentinel:** Validates U-Net approach for spatial conflict prediction. MC Dropout for uncertainty is directly applicable. Multi-target prediction (3 violence types) is similar to our multi-branch approach.

### STFT-VNNGP (arXiv: 2506.20935, June 2025)
- **Architecture:** Two-stage hybrid: (1) Sparse Temporal Fusion Transformer (TFT) for multi-quantile forecasts, (2) Variational Nearest Neighbor Gaussian Process (VNNGP) for spatiotemporal smoothing + uncertainty.
- **Data source:** GDELT event data.
- **Key innovation:** Handles sparsity, burstiness, and overdispersion in conflict event data -- exactly the problem with Sentinel's 1.5% positive rate.
- **Performance:** Won the 2023 ATD (Algorithms for Threat Detection) competition. Outperforms standalone TFT for timing and magnitude of bursty event periods, especially at long-range horizons.
- **Relevance to Sentinel:** Directly relevant architecture. TFT is interpretable (variable selection networks, temporal attention). GP layer handles calibrated uncertainty. Could replace or augment XGBoost for the continuation branch.

### Terrorism Relation-Aware GNN
- **Performance:** AUC-ROC 0.85 for organizational relationship mapping, F1 0.79 for regional pattern detection.
- **Relevance to Sentinel:** Validates GNN approach for conflict actor network analysis, relevant to actor_graph.py.

### Temporal Graph Networks (TGN, arXiv: 2006.10637)
- **Architecture:** Generalizes MPNNs to temporal graphs. Node memory module stores compressed representation of past interactions. Messages between interacting nodes update memories. Graph aggregation over temporal neighbors using features + memory.
- **Key components:** Memory module, message function, message aggregator, memory updater, embedding module.
- **Advantages:** Significantly outperforms previous approaches while being more computationally efficient.
- **2024 advances:** NAT (Neighborhood-Aware Temporal networks), cohesive temporal explanations via motifs, listwise ranking losses.
- **Relevance to Sentinel:** TGN's memory module could track per-hex conflict state over time. The "interaction-based memory update" maps to ACLED events updating hex states.

### Dynamic Spatial-Temporal GNNs (General)
- **DIDA:** Disentangled spatio-temporal attention for invariant vs variant patterns under distribution shift (NeurIPS 2022).
- **DSTAGNN:** Dynamic Spatial-Temporal Aware Graph NN replaces static adjacency with learned dynamic spatial dependency (ICML 2022).
- **Key pattern:** All high-performing models combine (1) spatial attention/convolution, (2) temporal modeling (LSTM/Transformer), (3) dynamic graph construction (vs static H3 adjacency).
- **Relevance to Sentinel:** Current plan uses static H3 ring-1/2/3 adjacency. Research shows dynamic adjacency (learned from data) significantly improves performance.

### GNNs for Crime Prediction (Transferable Methods)
- **MRAGNN:** Multi-type crime correlation learning. Leveraging correlations among different crime types enhances prediction accuracy.
- **ACSAformer:** Sparse attention + adaptive graph convolution for crime forecasting.
- **Crime hotspot prediction with GCN:** Demonstrated effectiveness of graph convolution for spatial event prediction with imbalanced data.
- **Relevance to Sentinel:** Crime prediction is structurally similar to conflict prediction (rare events, spatial clustering, temporal patterns). Methods transfer well.

---

## 4. Multimodal Fusion Architectures

### Cross-Attention for Heterogeneous Data
- **Mechanism:** Query (Q) from one modality, Key (K) and Value (V) from another. Dynamically aligns features across modalities.
- **CAFE:** Uses multiple processing units with cross-attention to capture temporal variations and spatial information, adapting feature weights from spatial aspects.
- **Recursive Joint Cross-Modal Attention:** Iterative fusion shown effective at CVPR 2024 workshop.
- **Key challenge:** Time-space conflicts, limited generalization, computational efficiency for large-scale processing, multi-source heterogeneous fusion.
- **Relevance to Sentinel:** Cross-attention between text embeddings (GDELT) and spatial features (hex time series) + satellite embeddings could be powerful for onset detection.

### Weather Foundation Model Fusion Patterns

#### Aurora (Microsoft, 1.3B params)
- **Architecture:** 3D Swin Transformer with 3D Perceiver-based encoders/decoders.
- **Training:** 1M+ hours of diverse geophysical data.
- **Fusion:** Perceiver encoders handle variable-length, heterogeneous inputs (pressure levels, surface variables). Swin Transformer captures spatial + vertical dependencies via shifted windows.
- **Transferable pattern:** Perceiver-based encoding of heterogeneous sensor inputs.

#### ClimaX (First weather FM)
- **Architecture:** Variable-separate tokenization -> variable aggregation -> position embedding + lead time embedding -> ViT backbone.
- **Training:** ERA5 + CMIP6 (truly vast, heterogeneous).
- **Transferable pattern:** Variable-separate tokenization. Each data source (ACLED, GDELT, FIRMS, weather) gets its own tokenizer, then aggregated before the main transformer.

#### FourCastNet / FCN2
- **Architecture:** ViT with Adaptive Fourier Neural Operators (AFNO). FCN2 upgraded to Spherical Harmonics Neural Operators (SFNO) for stability.
- **Transferable pattern:** Fourier-based operators for efficient long-range spatial dependencies. Could replace standard attention for H3 spatial processing.

#### FengWu
- **Architecture:** Multi-modal multi-task. Each atmospheric variable = individual modality. Cross-modal fuser transformer connects them. Replay buffer mechanism from RL for long-lead stability.
- **Transferable pattern:** Treat each data source as a separate modality with its own encoder, then fuse via cross-modal transformer. Replay buffer for temporal stability.

### Recommended Fusion Architecture for Sentinel
Based on weather FM patterns, a strong architecture would be:
1. **Per-source encoders:** Separate small transformers/MLPs for ACLED time series, GDELT text+events, FIRMS thermal, weather, satellite imagery
2. **Cross-modal fusion:** Cross-attention transformer layers (GDELT queries attend to ACLED keys, satellite queries attend to spatial context)
3. **Spatial aggregation:** GATv2 over H3 graph with fused per-hex embeddings
4. **Temporal integration:** LSTM or Temporal Transformer over daily sequences

---

## 5. Online/Continual Learning

### Core Methods

#### Elastic Weight Consolidation (EWC)
- **Mechanism:** Slows learning on weights important to previous tasks using Fisher Information Matrix (FIM). FIM identifies parameters that hold less information about previous tasks.
- **Published:** Kirkpatrick et al., PNAS 2017 (arXiv: 1612.00796).
- **Practical:** Good for small, periodic model updates. Compute FIM on current data, then regularize during retraining on new period.

#### Experience Replay (ER)
- **Mechanism:** Maintains small memory buffer of past data samples, replayed during training. Simpler than EWC and often competitive or superior.
- **Published:** Rolnick et al. (arXiv: 1811.11682).
- **Practical:** Most directly applicable to Sentinel. Keep buffer of past conflict events (especially rare onset events) and replay during monthly retraining.

#### Progressive Neural Networks
- **Mechanism:** New model per task with lateral connections to previous models. No forgetting by design, but grows linearly.
- **Practical:** Could use for region expansion -- Lebanon model -> Syria lateral connection -> global model.

#### Progress & Compress
- **Hybrid:** Combines Progressive Networks with EWC. Active column learns new task, then compressed into knowledge base using EWC.

### Adaptive Methods for Distribution Shift
- **Adaptive Memory Realignment (AMR):** Drift-detection module + drift-aware buffer update that preserves relevant past knowledge while adapting to evolving distributions.
- **DtACI:** Dynamically-tuned adaptive conformal inference for online learning under distribution shift.
- **Relevance to Sentinel:** Conflict dynamics shift with regime changes, new actors, political transitions. Monthly retraining with experience replay (keeping rare onset events in buffer) + EWC to protect learned spatial patterns.

### Practical Recommendation for Sentinel
1. **Monthly retraining** with experience replay buffer containing:
   - All true onset events (rare, must not be forgotten)
   - Representative negative samples
   - Recent 30 days of data
2. **EWC regularization** to protect learned spatial patterns while adapting to new conflict dynamics
3. **Drift detection** on feature distributions (GDELT tone shift, FIRMS baseline change) to trigger retraining

---

## 6. Conformal Prediction and Calibration

### BCCP -- Bin-Conditional Conformal Prediction (arXiv: 2410.14507)
- **Method:** Extends standard conformal prediction (SCP) by ensuring coverage rates across user-defined subsets (bins) of the outcome variable, not just in aggregate.
- **Key advantage:** SCP tends to over-cover in low-risk regions and under-cover in high-risk regions. BCCP fixes this by calibrating within bins.
- **Application:** Demonstrated on ViEWS fatality forecasting model. Prediction intervals achieve desired coverage across different fatality ranges.
- **Funded by:** ERC ViEWS project, Riksbankens Jubileumsfond, Norwegian Research Council.
- **Relevance to Sentinel:** Directly applicable. Define bins as alert tiers (Green/Yellow/Orange/Red) and calibrate within each. Ensures Red alerts have proper coverage, not just overall calibration.

### Adaptive Conformal Inference (ACI)
- **Method:** Online learning approach for prediction intervals under non-exchangeable data (time series). Models distribution shift as a learning problem in a single parameter, continuously re-estimated.
- **ACI (Gibbs & Candes, 2021):** Achieves desired coverage frequency over long intervals regardless of data generating process.
- **AgACI (ICML 2022):** Parameter-free version using online expert aggregation. arXiv: 2202.07282.
- **DtACI (Gibbs & Candes, 2024):** Dynamically-tuned version with improved adaptation.
- **Multi-step ACI:** Extended for multi-step ahead forecasting using MIMO strategy.
- **Relevance to Sentinel:** ACI handles the non-stationarity of conflict data naturally. Could provide calibrated 72h prediction intervals that adapt as conflict dynamics shift.

### Venn-ABERS Calibration
- **Method:** Distribution-free calibration using two isotonic regressions (one per class). Produces probability intervals [p0, p1] guaranteed to contain true class probability.
- **Key properties:**
  - Well-calibrated by design (theoretical guarantee)
  - Computationally efficient (single model, not ensemble)
  - Corrects both overconfident and underconfident models
  - Works well on imbalanced/rare event data
- **Performance:** Better calibrated than Platt scaling and isotonic regression on 22 datasets.
- **Implementation:** `venn-abers` Python library, compatible with scikit-learn.
- **Published:** UAI 2014. arXiv: 1211.0025.
- **Relevance to Sentinel:** Strong candidate for calibrating XGBoost outputs. Produces intervals rather than point estimates -- "risk is between 0.65-0.78" rather than "risk is 0.72". Handles the 1.5% positive rate well.

### Extreme Conformal Prediction (arXiv: 2505.08578)
- **Method:** Reliable intervals specifically for high-impact rare events.
- **Relevance to Sentinel:** Directly addresses the tail of conflict intensity distribution.

### Recommended Calibration Stack for Sentinel
1. **Venn-ABERS** on each branch output (fast, guaranteed calibration)
2. **BCCP** on meta-learner output (bin-conditional by alert tier)
3. **ACI** for live scoring (adapts to distribution shift over time)

---

## 7. Satellite Imagery for Conflict

### SAR Coherence for Building Damage

#### Pixel-Wise T-Test (PWTT)
- **Method:** Lightweight, unsupervised algorithm using Sentinel-1 backscatter amplitude. T-test measures difference between pre/post-conflict means adjusted by standard deviation. Maintains 10m native resolution.
- **Performance:** AUC=0.88 across Ukraine, 0.81 in Gaza. Building-level accuracy rivaling deep learning methods using high-res imagery.
- **Implementation:** Single line of code via Google Earth Engine Python API. Open source: `github.com/oballinger/PWTT`.
- **Published:** Remote Sensing of Environment 2025. arXiv: 2405.06323.
- **Used by:** The Economist for Ukraine damage assessment.

#### Long Temporal-Arc Coherent Change Detection (LT-CCD)
- **Method:** InSAR coherence tracking with weekly temporal fidelity. Applied to Gaza (Oct 2023 - Oct 2024).
- **Performance:** Detects 92.5% of UNOSAT damage labels, 1.2% false positive rate. Found 191,263 buildings (3/5 of all buildings) damaged or destroyed.
- **Published:** arXiv: 2506.14730 (June 2025).
- **Temporal insights:** Detected damage pause during temporary ceasefire, conflict hotspot shifts from north to south Gaza.

#### Combined Optical-SAR Approach
- **Method:** Sentinel-1 SAR + Sentinel-2 optical fusion. Combined approach outperforms either single-sensor method in producer's and user's accuracy, especially for moderate damage.
- **Published:** Remote Sensing 2022, MDPI.

### Change Detection with Deep Learning
- **DeepDamageNet:** Two-step: damage segmentation -> classification from satellite imagery.
- **DDNet:** Dual-temporal joint attention network for disaster damage detection.
- **DisasterAdaptiveNet:** Multi-hazard building damage detection from VHR imagery.
- **Performance:** Best models achieve F1 ~88% on test data, 86% fine-tuned to new domains.
- **Architectures:** Siamese Transformer encoder + dual-task decoder outperforms ConvNets. Mamba (state space models) emerging for efficiency.

### Vehicle/Infrastructure Detection
- At Sentinel-2's 10m resolution, individual vehicle detection is not feasible. However:
  - Road network changes detectable
  - Large infrastructure (airports, ports, bridges) damage visible
  - Military installations and camps detectable at aggregate level
  - Change in built-up area density measurable

### CrisisReady (Harvard/Direct Relief)
- **ReadyMapper tool:** Tracks population movement and relocation during disasters using mobility data + satellite imagery.
- **Tukul detector:** ML algorithm for automatic identification of traditional structures from satellite imagery.
- **Focus:** Translational readiness -- converting data insights into actionable strategies for humanitarian response.

### Bellingcat Methodology
- **Geolocation:** Sun position, shadow analysis (SunCalc), landmark matching, Google Earth comparison.
- **Verification:** CE90 (Circular Error 90th percentile) and RMSE accuracy standards.
- **Tools:** satellites.pro for quick switching between free satellite services, Shadow Finder for chronolocation.
- **Relevance to Sentinel:** Methodology for validating model predictions against actual events.

---

## 8. Social Media as Conflict Signal

### Telegram OSINT
- **Role:** Primary information source for Ukraine/Russia conflict. Half the population in both countries use it as primary news channel. Hamas uses it for communications and information warfare.
- **Tools:** Extensive open-source repository of tools (`The-Osint-Toolbox/Telegram-OSINT`). Bot-based monitoring, channel tracking, metadata extraction.
- **Languages:** OSINT tools can analyze Arabic, Farsi, English. Palestinian militancy communication surfaces in Arabic (internal) and English (external).
- **Scale:** Syria's 11-year conflict generated ~5M digital records. Ukraine produced 2.8M pieces of documentation in a single year.
- **Monitoring approaches:** Real-time channel monitoring, keyword tracking, sentiment analysis, post velocity measurement, media (image/video) counting.
- **Relevance to Sentinel:** 20_ingest_telegram.py should target 5-10 public aggregator channels. Features: post_count, threat_keywords, media_count, post_velocity_3d, sentiment_shift per hex-day.

### Arabic Twitter/X Analysis
- **Research:** Active research on Arabic tweet sentiment analysis for crisis prediction. Machine learning outperforms lexicon-based methods (85.5% accuracy with Logistic Model Trees).
- **Conflict applications:** Sentiment analysis applied to Syrian civil war tweets. Emotions serve as indicators of positions and attitudes in war/conflict contexts.
- **Challenge:** Dialectal variation (Lebanese, Palestinian, Syrian Arabic all differ). CAMeL Tools' dialect identification needed for preprocessing.

### TikTok as Documentation Platform
- **Role:** Short-form video documentation of drone strikes, frontline activity, civilian impact. Spreads faster than official briefings.
- **Verification challenge:** AI-manipulated footage emerging. Generative video tools can produce convincing explosion sequences. Timestamp/location watermarks can be faked.
- **OSINT methods:** Geolocation via Google Earth, SunCalc shadow analysis, landmark matching. Bellingcat uses Telegram channel to catalog TikTok videos for verification.
- **Relevance to Sentinel:** TikTok content velocity could serve as a real-time conflict intensity indicator, but verification pipeline needed.

### Internet Shutdown Detection

#### IODA (Internet Outage Detection and Analysis)
- **Operated by:** CAIDA (now at Georgia Tech).
- **Methods:** Three complementary signals:
  1. **BGP:** ~500 monitors from RouteViews + RIPE RIS for control plane reachability
  2. **Active Probing:** Trinocular method, ICMP echo requests across IPv4 address space
  3. **Internet Background Radiation:** UCSD Network Telescope monitoring unutilized /8 block
- **Capabilities:** Near-real-time detection of macroscopic outages affecting AS or country fractions. Can differentiate shutdowns from spontaneous outages, detect throttling and route changes.
- **Relevance to Sentinel:** Feature: connectivity_score, delta_24h, outage_flag per country/AS. Government-ordered shutdowns are strong conflict escalation signals.

#### OONI (Open Observatory of Network Interference)
- **Founded:** 2012. Millions of measurements from 200+ countries.
- **Method:** OONI Probe app measures blocking of websites, messaging apps, circumvention tools. Scans TCP, DNS, HTTP, TLS for tampering. Checks DNS spoofing, keyword filtering, transparent proxying, block lists.
- **Data access:** OONI Explorer + OONI API, measurements published within minutes.
- **Case studies:** Confirmed Iran 2019 blackout, Cuba referendum censorship.
- **Relevance to Sentinel:** Features: blocked_app_count, censorship_flag, new_blocks_24h. App blocking (WhatsApp, Signal, Telegram) is a pre-escalation indicator.

#### Cloudflare Radar
- **Capabilities:** Real-time traffic anomaly detection across global network. Outage Center (CROC) with API access for traffic anomalies.
- **API:** Free access. `GET /radar/traffic_anomalies` returns detected outages with country/AS granularity.
- **Civil society:** Partners with OONI and human rights organizations. Alerts on significant traffic drops (often government-ordered shutdowns).
- **Relevance to Sentinel:** Complementary to IODA. Higher temporal resolution (near-real-time). Could trigger tactical alerts when connectivity drops detected in Levant region.

---

## 9. Critical Research Papers and Findings

### "Common Indicators Hurt Armed Conflict Prediction" (arXiv: 2503.00265, March 2025)
- **Finding:** Specifying conflict type negatively impacts predictability of conflict intensity (fatalities, duration, size).
- **Method:** Unsupervised learning identifies 3 conflict types: "major unrest," "local conflict," "sporadic and spillover events." Types stratify into hierarchy: population > infrastructure > economics > geography.
- **Implication for Sentinel:** Don't over-specialize the model on conflict subtypes. The meta-learner should predict "dangerous" broadly rather than trying to predict specific event types separately.

### "Do Large Language Models Know Conflict?" (arXiv: 2505.09852, May 2025)
- **Finding:** LLMs (GPT-4, LLaMA-2) tested on Horn of Africa and Middle East conflict forecasting (2020-2024).
- **Parametric vs non-parametric:** RAG with ACLED/GDELT context significantly improves over pure parametric knowledge.
- **Implication for Sentinel:** Validates the Gemini + Google Search grounding approach for alerting_agent.py. RAG with structured conflict data >> pure LLM knowledge.

### LLM Forecasting Performance Trajectory
- **Best model:** GPT-4.5 achieves Brier score 0.101 vs superforecasters' 0.081.
- **Projection:** LLM-superforecaster parity estimated late 2026 (95% CI: Dec 2025 - Jan 2028).

### VIEWS 2023/24 Prediction Challenge
- **Participants:** 13 teams, 23 models.
- **Task:** Forecast fatalities as probability distributions (not just point estimates).
- **Top performers:** VIEWS' Conflictology benchmark, Observed Markov Model, Bayesian Negative Binomial GLMM, Forests of UncertainTrees (subnational).
- **Evaluation:** CRPS, ab-Log Score, MIS -- metrics that reward both accuracy AND honest uncertainty.
- **Implication for Sentinel:** Probability distributions + uncertainty quantification is the standard, not optional. Conformal prediction / MC Dropout needed.

### Spatiotemporal CNN Conflict Fatality Prediction (Remote Sensing, 2024)
- **Method:** CNN + satellite imagery for spatiotemporal prediction of conflict fatality risk.
- **Relevance:** Validates that satellite imagery adds signal beyond structured data for conflict prediction.

---

## 10. Synthesis: Recommendations for Sentinel ML Pipeline

### Highest-Impact Additions (Ordered by Expected Value)

1. **Text encoding with AraBERT/SONAR** (onset detection): Mueller & Rauh show text AUC 0.83 for onset. AraBERT for Arabic, SONAR for multilingual. Encode GDELT titles + ACLED notes -> 32d PCA embeddings + embedding_shift features.

2. **Conformal calibration stack** (Venn-ABERS + BCCP + ACI): Research shows Venn-ABERS is guaranteed well-calibrated, BCCP handles per-tier calibration, ACI adapts to distribution shift. Replace arbitrary 0.75 threshold with calibrated intervals.

3. **TGN-style memory module for GNN** (spatial spreading): TGN's node memory naturally tracks per-hex conflict state. More principled than raw temporal lags. Memory updates from ACLED events.

4. **PWTT SAR damage detection as feature** (near-real-time): AUC 0.88 for building damage with one line of GEE code. Feed damage_ratio per hex as input feature. Particularly powerful for onset detection (new damage in previously undamaged area).

5. **Internet shutdown detection** (IODA + Cloudflare Radar as features): Government shutdowns are strong pre-escalation signals. connectivity_delta per country/AS is a leading indicator.

6. **Experience replay for monthly retraining**: Keep buffer of all onset events + recent data. EWC regularization to protect learned spatial patterns.

7. **Dynamic graph adjacency** (learned, not static H3 rings): Research consistently shows dynamic adjacency outperforms static. Learn which hexes influence each other from data.

8. **Temporal Fusion Transformer** (for continuation branch): STFT-VNNGP won ATD competition. TFT handles bursty, sparse conflict data better than standard approaches. Interpretable variable selection.

### Architecture Patterns from Weather FMs
- **Variable-separate tokenization** (ClimaX): Each data source gets its own tokenizer
- **Perceiver-based encoding** (Aurora): Handle variable-length heterogeneous inputs
- **Cross-modal fusion transformer** (FengWu): Separate modality encoders + cross-attention fusion
- **Replay buffer** (FengWu): Stabilize long-horizon predictions

### Models to Explore for Satellite Embeddings
- **Clay v1.5** (best fit): Multi-sensor (S1+S2+Landsat), open source, 768d embeddings, LoRA fine-tuning
- **CROMA** (SAR+optical fusion): Purpose-built for S1+S2, spatial ALiBi, NeurIPS 2023
- **SatCLIP** (location embeddings): Replace raw lat/lon with learned 256d location vectors
- **Prithvi-EO-2.0** (NASA backing): 600M params, HLS data, terratorch fine-tuning toolkit

---

## Sources

### Geospatial Foundation Models
- [Prithvi-EO-2.0 - IBM Research](https://research.ibm.com/blog/prithvi2-geospatial)
- [Prithvi-EO-2.0 arXiv](https://arxiv.org/abs/2412.02732)
- [Prithvi-EO-2.0 GitHub](https://github.com/NASA-IMPACT/Prithvi-EO-2.0)
- [Prithvi-EO-2.0 Hugging Face](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-600M)
- [PEFT for Geospatial FMs](https://arxiv.org/html/2504.17397v1)
- [Clay Foundation Model Docs](https://clay-foundation.github.io/model/index.html)
- [Clay GitHub](https://github.com/Clay-foundation/model)
- [Clay Hugging Face](https://huggingface.co/made-with-clay/Clay)
- [Clay Architecture - DeepWiki](https://deepwiki.com/Clay-foundation/model/2-model-architecture)
- [SatCLIP arXiv](https://arxiv.org/abs/2311.17179)
- [SatCLIP GitHub](https://github.com/microsoft/satclip)
- [GeoCLIP NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b57aaddf85ab01a2445a79c9edc1f4b-Paper-Conference.pdf)
- [SkySense CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Guo_SkySense_A_Multi-Modal_Remote_Sensing_Foundation_Model_Towards_Universal_Interpretation_CVPR_2024_paper.pdf)
- [SkySense GitHub](https://github.com/Jack-bo1220/SkySense)
- [SkySense V2 - Nature Machine Intelligence 2025](https://arxiv.org/html/2507.13812v1)
- [SpectralGPT arXiv](https://arxiv.org/abs/2311.07113)
- [SatMAE arXiv](https://arxiv.org/abs/2207.08051)
- [CROMA arXiv](https://arxiv.org/abs/2311.00566)
- [CROMA GitHub](https://github.com/antofuller/CROMA)
- [RingMo 3.0 - Chinese Academy of Sciences](https://english.cas.cn/newsroom/news/202409/t20240924_690403.shtml)
- [AlphaEarth Foundations - Google DeepMind](https://deepmind.google/blog/alphaearth-foundations-helps-map-our-planet-in-unprecedented-detail/)
- [Google Earth AI Blog](https://research.google/blog/google-earth-ai-unlocking-geospatial-insights-with-foundation-models-and-cross-modal-reasoning/)
- [Awesome Remote Sensing Foundation Models](https://github.com/Jack-bo1220/Awesome-Remote-Sensing-Foundation-Models)

### NLP for Conflict
- [Mueller & Rauh - Conflict Forecast](https://conflictforecast.org/about)
- [Mueller & Rauh - Hard Problem of Prediction](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3395185)
- [Mueller & Rauh - Reading Between the Lines](https://ideas.repec.org/p/bge/wpaper/990.html)
- [AraBERT arXiv](https://arxiv.org/abs/2003.00104)
- [AraBERT GitHub](https://github.com/aub-mind/arabert)
- [AlephBERT arXiv](https://ar5iv.labs.arxiv.org/html/2104.04052)
- [HeRo Hebrew Models arXiv](https://arxiv.org/pdf/2304.11077)
- [CAMeL Tools GitHub](https://github.com/CAMeL-Lab/camel_tools)
- [CAMeL Lab - NYU Abu Dhabi](https://nyuad.nyu.edu/en/research/faculty-labs-and-projects/computational-approaches-to-modeling-language-lab.html)
- [SONAR - Meta AI](https://ai.meta.com/research/publications/sonar-sentence-level-multimodal-and-language-agnostic-representations/)
- [Sentence Transformers Docs](https://sbert.net/)
- [Arabic Sentence Transformer Benchmarks](https://github.com/m-elbeltagi/Comparing_Arabic_Sentence_Transformers)

### GNNs for Conflict
- [HydraNet / Next-Gen Conflict Forecasting arXiv](https://arxiv.org/abs/2506.14817)
- [STFT-VNNGP Geopolitical Forecasting arXiv](https://arxiv.org/abs/2506.20935)
- [TGN arXiv](https://arxiv.org/abs/2006.10637)
- [TGN GitHub](https://github.com/twitter-research/tgn)
- [Temporal Graph Learning in 2024](https://towardsdatascience.com/temporal-graph-learning-in-2024-feaa9371b8e2/)
- [DIDA - Dynamic GNNs Under Distribution Shift (NeurIPS 2022)](https://papers.neurips.cc/paper_files/paper/2022/file/2857242c9e97de339ce642e75b15ff24-Paper-Conference.pdf)
- [DSTAGNN (ICML 2022)](https://proceedings.mlr.press/v162/lan22a/lan22a.pdf)
- [GNN for Temporal Terrorist Network Analysis](https://link.springer.com/article/10.1007/s41870-025-02914-1)

### Multimodal Fusion
- [Aurora arXiv](https://arxiv.org/html/2405.13063v2)
- [Aurora - Nature 2025](https://www.nature.com/articles/s41586-025-09005-y)
- [ClimaX ICML 2023](https://proceedings.mlr.press/v202/nguyen23a/nguyen23a.pdf)
- [FourCastNet / SFNO](https://openreview.net/pdf/d616be3086e1271a158fefc358a6dada32f3acb1.pdf)
- [Deep Multimodal Data Fusion Survey (ACM 2024)](https://dl.acm.org/doi/full/10.1145/3649447)
- [Cross-Attention for Text and Image (Stanford)](https://web.stanford.edu/class/archive/cs/cs224n/cs224n.1254/final-reports/256711050.pdf)

### Continual Learning
- [EWC - PNAS 2017](https://www.pnas.org/doi/10.1073/pnas.1611835114)
- [Experience Replay arXiv](https://arxiv.org/pdf/1811.11682v1)
- [Continual Learning Survey arXiv](https://arxiv.org/html/2403.05175v1)
- [EVCL arXiv](https://arxiv.org/html/2406.15972v1)
- [Adaptive Memory Realignment arXiv](https://arxiv.org/html/2507.02310v1)

### Conformal Prediction & Calibration
- [BCCP arXiv](https://arxiv.org/abs/2410.14507)
- [ACI arXiv](https://arxiv.org/abs/2202.07282)
- [ACI - Gibbs & Candes 2021](https://openreview.net/forum?id=6vaActvpcp3)
- [Venn-ABERS Predictors arXiv](https://arxiv.org/abs/1211.0025)
- [Venn-ABERS Python Library](https://github.com/ip200/venn-abers)
- [Extreme Conformal Prediction arXiv](https://arxiv.org/html/2505.08578)
- [Conformal Prediction Benchmarking](https://arxiv.org/html/2601.18509v2)

### Satellite Imagery for Conflict
- [PWTT arXiv](https://arxiv.org/abs/2405.06323)
- [PWTT GitHub](https://github.com/oballinger/PWTT)
- [PWTT Dashboard](https://oballinger.github.io/PWTT/)
- [Ukraine Sentinel-1 Open-Source Tool](https://www.nature.com/articles/s43247-025-02183-7)
- [Gaza Active InSAR Monitoring arXiv](https://arxiv.org/abs/2506.14730)
- [Kyiv Damage Assessment (S1+S2)](https://www.mdpi.com/2072-4292/14/24/6239)
- [CNN Conflict Fatality Prediction from Satellite](https://www.mdpi.com/2072-4292/16/18/3411)
- [DeepDamageNet arXiv](https://arxiv.org/html/2405.04800v1)
- [CrisisReady](https://www.crisisready.io/)
- [Bellingcat Investigation Toolkit](https://bellingcat.gitbook.io/toolkit/)

### Social Media & Internet Monitoring
- [Telegram OSINT GitHub](https://github.com/The-Osint-Toolbox/Telegram-OSINT)
- [Telegram Warfare - Fathom Journal](https://fathomjournal.org/telegram-warfare-the-new-frontier-of-psychological-warfare-in-the-israel-palestine-conflict/)
- [TikTok War - Fletcher School](https://sites.tufts.edu/fletcherrussia/the-tiktok-war-how-ukraines-civilians-rewrote-the-information-battlefield/)
- [IODA - CAIDA](https://www.caida.org/projects/ioda/)
- [IODA - APNIC Blog](https://blog.apnic.net/2024/09/11/ioda-internet-outage-detection-and-analysis/)
- [OONI](https://ooni.org/)
- [Cloudflare Radar](https://radar.cloudflare.com/)
- [Cloudflare Radar API](https://developers.cloudflare.com/api/resources/radar/)
- [Cloudflare Radar Outage Center](https://radar.cloudflare.com/outage-center)

### Critical Analysis Papers
- [Common Indicators Hurt Conflict Prediction arXiv](https://arxiv.org/abs/2503.00265)
- [LLMs for Conflict Forecasting arXiv](https://arxiv.org/abs/2505.09852)
- [VIEWS Prediction Challenge 2023/24](https://viewsforecasting.org/research/prediction-challenge-2023/)
- [VIEWS Prediction Challenge Paper arXiv](https://arxiv.org/abs/2407.11045)
- [VIEWS Leaderboard](https://viewsforecasting.org/research/prediction-challenge-2023/leaderboard/)
- [Armed Conflict Risk Under Climate Change - Nature Communications](https://www.nature.com/articles/s41467-022-30356-x)
- [ML and Conflict Prediction Use Case](https://stabilityjournal.org/articles/10.5334/sta.cr)
