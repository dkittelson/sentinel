# Conflict Prediction Industry — Comprehensive Analysis

## 1. The Academic Landscape: Who's Building What

The field is dominated by **ViEWS** (Uppsala/PRIO), the gold standard — an ensemble of ~16 models generating monthly forecasts at PRIO-GRID (~55km) and country level, funded by two ERC Advanced Grants (~EUR 2.5M+). ViEWS achieves AUPR >0.90 at 1-6 months but degrades to ~0.80 at 2-3 years. Their 2023/24 Prediction Challenge drew 15+ teams evaluated on CRPS (probabilistic scoring).

**ACLED CAST** uses LightGBM with Tweedie objective and hierarchical reconciliation, forecasting at Admin1 level in four-week rolling periods with conformal inference for uncertainty.

**Mueller & Rauh** (Barcelona/Cambridge) demonstrated text-only onset AUC of 0.83 using LDA on 4M newspaper articles — text dominates for "hard onset" cases (no violence 10+ years) where history-based AUC drops to 0.63.

**HydraNet** (arXiv:2506.14817) — MC Dropout LSTM U-Net — is current SOTA, beating ViEWS on Average Precision for all three violence types using zero manual feature engineering, trained in ~2 hours on a V100.

Every system struggles with onset prediction — EURIDICE's hard-onset benchmark peaks at AUC-PR 0.363. This is the frontier Sentinel targets.

## 2. The Commercial Market: Who's Selling What

**Tier 1 (Defense platforms):** Palantir ($4.48B revenue, $10B Army contract, ~$371B market cap) sells data integration, not prediction. Recorded Future (acquired by Mastercard for $2.65B) indexes 1M+ sources. Dataminr ($4.1B valuation, $282M DoD contract) detects events from social media in real-time.

**Tier 2 (Geopolitical risk):** Verisk Maplecroft, S&P Global, EIU, Control Risks (~3,400 employees) — all country-level, analyst-driven, $50K-200K+/year.

**Tier 3 (Emerging):** Hala Systems is closest to Sentinel — IoT sensors providing 15 min airstrike warning in Syria, correlated with 10-30% casualty reduction. But hardware-dependent and theater-specific. FiscalNote/Predata analyzes metadata across 300K+ sources. GeoQuant (acquired by Fitch) for political risk scoring.

**Tier 4 (Satellite):** Maxar ($3.2B NRO contract), BlackSky (90-min image delivery), Planet ($230M Asia-Pacific deal).

Total risk analytics market: ~$42B at 10-15% CAGR. Geopolitical/conflict subset: $2-4B. No commercial competitor offers hex-level resolution at daily grain for civilian users.

## 3. The Onset Problem: The Hardest and Most Valuable Challenge

Chadefaux & Schincariol (2025) formally proved autoregressive models using only lagged violence match models with structural covariates — conflict is highly persistent. Mueller & Rauh's "Hard Problem" (JEEA 2022): inside the conflict trap, onset is easy; outside it, onset is very unlikely and hard to forecast.

OCHA's 2023 assessment: "insufficient justification for exclusively relying on conflict prediction models to drive anticipatory action" due to poor onset performance. Onset AUC-PR targets: >0.03 = real signal, >0.08 = good, >0.15 = suspicious.

Features that drive onset: text/media signals (Mueller & Rauh AUC 0.75 on hard cases), internet shutdowns (near-zero FPR), Telegram OSINT (12-48h lead), food price spikes (NECSI predicted Arab Spring). Temporal lags are near-zero by definition for onset — a model whose top SHAP features are lags has not learned onset.

## 4. Foundation Models and Deep Learning

**Geospatial FMs:** Clay v1.5 (632M params, S1+S2+Landsat, 768d embeddings, Apache) is best fit for per-hex satellite embeddings. CROMA (NeurIPS 2023) fuses S1+S2 with spatial ALiBi. Prithvi-EO-2.0 (NASA/IBM, 600M params) beats previous SOTA by 8%. LoRA matches full fine-tuning for all three.

**NLP:** AraBERT: 99% F1 on Arabic classification. SONAR (Meta, 200 languages): best unified Arabic+Hebrew+English embedding space. ConfliBERT (arXiv:2412.15060): domain-specific BERT outperforms Gemma 2 (9B), Llama 3.1 (7B), Qwen 2.5 (14B) on conflict tasks.

**GNNs:** STFT-VNNGP (TFT + GP) won 2023 ATD competition — 58% MAE reduction on bursty conflict data. TGN memory module maps to per-hex state tracking. Dynamic graph adjacency consistently outperforms static H3 rings.

**Weather FM patterns that transfer:** ClimaX variable-separate tokenization, Aurora Perceiver encoding for heterogeneous inputs, FengWu cross-modal fusion with replay buffer. Critical: arXiv:2503.00265 shows over-specializing on conflict subtypes hurts performance.

## 5. Calibration: What Buyers Actually Need

Recommended stack: **Venn-ABERS** per branch (guaranteed calibration, probability intervals), **BCCP** (arXiv:2410.14507) on meta-learner (bin-conditional by alert tier; built on ViEWS), **ACI** for live scoring (handles non-stationarity).

ViEWS challenge uses CRPS as primary metric — point predictions without calibration are incomplete. ACLED CAST already uses conformal inference. ECE < 0.05 is standard.

Political risk insurers (Lloyd's, AIG) increasing capacity 50% ($20M→$30M per line). Premiums at 1% of coverage. They need calibrated probabilities to price policies — currently using country-level scores. Hex-level is a step change.

## 6. Satellite Intelligence: Free Resources That Work

**PWTT** (arXiv:2405.06323): AUC=0.88 for building damage from Sentinel-1 with one line of GEE code. Used by The Economist for Ukraine assessment. **LT-CCD InSAR** (arXiv:2506.14730): detects 92.5% of UNOSAT damage in Gaza, 1.2% FPR, 191K buildings. Combined S1+S2 outperforms either sensor alone.

Clay FM generates 768d per-hex embeddings. SatCLIP (Microsoft, AAAI 2025) provides learned 256d location vectors. Honest gap: no free source gives daily 50cm revisit for troop movement detection. Pragmatic: free Sentinel for baseline, commercial tasking for onset hexes.

## 7. Social Media and Internet Monitoring

**Telegram:** Primary info channel in conflict zones. Notre Dame (2024): imagery spike from 989 Russian military bloggers predicted Ukraine invasion. Aggregator channels capture signals 12-24h before international media.

**IODA** (Georgia Tech): combines BGP routing, active probing, and background radiation. Internet shutdowns preceded military action in Myanmar, Sudan, Tigray — lowest FPR leading indicator.

**OONI** (200+ countries): targeted app-level block detection (WhatsApp/Signal/Telegram blocked = suppression incoming). **Cloudflare Radar**: free API, ~20% global web traffic. Triangulating IODA + OONI + Cloudflare gives highest-confidence outage detection.

## 8. The Buyer Landscape

**Government:** Pentagon spent $1.3B on Palantir Maven. OTA is best vehicle for startups — no FAR compliance. SBIR frozen (expired Oct 2025); when active, Phase I ~$150K, Phase II ~$1M.

**Humanitarian:** UN DPPA Innovation Cell works with Stanford/MIT. OCHA has anticipatory action in 12+ countries but limited conflict prediction use.

**Insurance:** PRI capacity ~$4B (2025). Gulf war risk premiums rose 5x. Hex-level data could power underwriting.

**Finance:** GeoQuant/Fitch for political risk scoring. BlackRock Geopolitical Risk Dashboard. Geopolitical events move commodity markets 30-50%.

**Defense VC:** In-Q-Tel ($750M AUM), Lux Capital ($200M defense fund), a16z (14 defense deals), Founders Fund, Shield Capital. Defense tech VC at $28.1B through H1 2025.

## 9. Ethics, Legal, and Deployment

**Bias:** ACLED underreports rural events; GDELT accuracy ~55% with ~20% duplication and capital-city bias. Systems trained on both underestimate risk in poor-coverage areas.

**Dual-use:** Israel's Lavender/Gospel used prediction for automated targeting. Strava exposed military bases. Ukraine's Diia blurs civilian and intelligence functions.

**EU AI Act** (August 2026): conflict prediction processing location data likely classified high-risk. **ICRC 2024:** cannot accept life-and-death decisions delegated to machines.

**Deployment:** Alert fatigue is existential — 69% opt-out after excessive messaging. Offline-first is non-negotiable (2G at ~20kbps). Push messages under 100 chars show higher open rates.

## 10. Case Studies

**Rwanda 1994:** Warning existed — arms flows, militia training documented. UNAMIR denied permission to act. Failure of political will, not prediction.

**Ukraine 2022:** US had Russian plans from Oct 2021. OSINT researcher caught Google Maps traffic jam 1 hour before invasion. Best early warning case in modern history — SIGINT + OSINT + public sharing.

**October 7, 2023:** Israel had Hamas's attack plan since 2018. Junior analysts wrote warning reports. Sentries observed training. Failure: groupthink — establishment believed Hamas was "adapting to governance." Perfect systems are useless if culture dismisses outputs.

**Tigray 2020-22:** FEWS NET flagged famine May 2021. System worked. UNSC vetoes blocked response.

## 11. Where Sentinel Sits

**Differentiators:** (1) H3 hex-6 (~36km2) vs PRIO-GRID (~2,500km2). (2) Daily grain / 72h lookahead vs monthly. (3) Civilian-first — no competitor targets civilians as primary user. (4) Actionable output (evac routing, shelter awareness, push) vs dashboards. (5) Foundation model targeting onset.

**Risks:** (1) No proprietary data source. (2) Onset is the hardest unsolved problem. (3) ACLED licensing at scale. (4) Liability under EU AI Act.

**Moat:** Human feedback loop (analyst marks FP/TP/missed → labels feed retraining → model improves). More users → better labels → better model → more users. Compounds over time.

**Revenue:** Free for civilians. Monetize: NGO API ($5K-50K/month), government OTA contracts ($200K-1M), calibrated probability feeds to insurers (highest margin).

**Credibility path:** Publish at JPR/Political Analysis. Free public dashboard with 7-day delay. Be first to correctly call major events with published prediction timelines.

## Sources

Academic: ViEWS (viewsforecasting.org), Mueller & Rauh (conflictforecast.org), HydraNet (arXiv:2506.14817), DynAttn (arXiv:2512.21435), STFT-VNNGP (arXiv:2506.20935), ConfliBERT (arXiv:2412.15060), BCCP (arXiv:2410.14507), EURIDICE benchmarks, Chadefaux 2025 (EPJ Data Science). Foundation Models: Clay v1.5, Prithvi-EO-2.0 (NASA/IBM), CROMA (arXiv:2311.00566), SatCLIP (Microsoft), SONAR (Meta), AraBERT, PWTT (arXiv:2405.06323). Commercial: Palantir 10-K, Recorded Future ($2.65B), Dataminr ($4.1B), Hala Systems, GeoQuant/Fitch. Market: ~$42B risk analytics (GII Research), ~$4B PRI (Lloyd's), $28.1B defense VC H1 2025 (Dakota). Policy: ICRC AI Policy 2024, EU AI Act, UN New Agenda for Peace 2023, OCHA 2023 assessment. Full 560-line research: `/research/foundation_models_deep_learning_conflict.md`
