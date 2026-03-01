## Inspiration

On October 7, 2023, thousands of civilians in southern Israel had no warning. In September 2024, Hezbollah pager bombs detonated across Lebanon with zero public notice. In 2025, US-Iran tensions pushed the Strait of Hormuz to the brink — oil workers, journalists, and aid organizations operating in the region had no systematic way to know where the next flashpoint would be.

The pattern is always the same: conflict escalates gradually, the signals are there in the data — troop movements, news tone shifts, historical incident clusters — but no tool synthesizes them into something a civilian can act on. Governments get intelligence briefings. Civilians get nothing.

Sentinel is our answer to that gap.

## What it does

Sentinel monitors the Levant corridor (Lebanon, Israel, Syria) in real time, scoring every 36 km² hex on the map with a 72-hour danger probability. It fuses three live data streams — ACLED conflict events, NASA FIRMS thermal anomalies, and GDELT global news sentiment — through a trained XGBoost model. When you click any hex, a Gemini agent searches live news and writes a plain-language intelligence briefing grounded in real sources. A backtest mode lets you replay history — watch the heatmap light up in the days before October 7.

## How we built it

- **ML pipeline**: 8.5 million hex-day training samples, XGBoost with focal loss, 44 features including spatial lag from H3 ring-1 neighbors, temporal lags, and actor novelty signals. ROC-AUC 0.873.
- **Backend**: FastAPI + Supabase (PostGIS), APScheduler re-scoring every 15 minutes, two-layer alerting (strategic ML + tactical rule-based).
- **Intelligence layer**: Gemini 2.5 Flash with Google Search grounding — the LLM searches real news, not hallucinations. Backtest mode instructs the agent to retrieve historical news for that specific date.
- **Frontend**: React + Mapbox GL JS, H3 hex overlay with YlOrRd gradient heatmap, hospital shelter layer, AI-powered evacuation routing.

## Challenges we ran into

The hardest problem was the Bayes error ceiling on conflict prediction. After 23 experiments, we accepted that geopolitical violence has irreducible unpredictability — the model's job is to flag elevated risk, not predict the exact moment of an attack. We shifted from maximizing precision to maximizing recall, because over-warning is survivable; missing a warning is not.

Getting the LLM to not contradict the heatmap was the second challenge. Early versions of the intelligence summary would say "low probability of danger" for a RED hex, because Gemini interpreted a 54% raw probability score as low. The fix: strip raw numbers from the prompt entirely and give the LLM a human-readable tier description ("HIGH RISK — active conflict zone") with an explicit instruction to never downplay it.

## Accomplishments that we're proud of

The backtest demo is visceral. You start on September 30, 2023 — the map is mostly yellow. You play forward day by day. By October 8, southern Israel and northern Gaza are dark red. The model saw it coming. That's the whole point.

## What we learned

Data fusion is more powerful than any single model. The GDELT news sentiment and NASA FIRMS thermal signals each individually add measurable lift. A burning field and a spike in hostile news coverage in the same hex on the same day is a signal no single dataset could catch alone.

## What's next for Sentinel

Expand beyond the Levant — Ukraine, Sudan, Myanmar are the next priority regions. Add FCM push alerts so civilians get notified when a hex they're near flips to RED. Build the proactive monitoring agent that scans all high-risk hexes every 15 minutes and pushes alerts before a user even opens the app. The infrastructure is built. The data pipeline generalizes. Sentinel can cover any conflict zone on Earth.
