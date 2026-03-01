ML Pipeline
Raw APIs → Spatial Preprocessing → ML Model →  AI Agent → Final Output
Raw APIs: Ingest historical conflict data (ACLED), live news sentiment (GDELT), and live thermal satellite data (NASA FIRMS).
Spatial Preprocessing: Group all the raw coordinate data into uniform hexagonal geographical bins (using Uber's H3 library) and calculate rolling averages for each hex.
ML Model (XGBoost): The model takes the features for a specific hex and outputs a probability score (0.0 to 1.0) of an imminent violent event.
AI Agent (LLM): If the score crosses the "Red" threshold (e.g., > 0.7), an LLM reads the specific features that triggered it (e.g., "thermal spike + troop movement news") and drafts a human-readable warning.
Final Output: A numeric risk tier (Yellow, Orange, Red) and a localized alert message.

App
Database (PostgreSQL + PostGIS): Stores the H3 hex grids, the ingested API data, and the latest risk scores for every location. (PostGIS is crucial here because it is built for querying geographic coordinates).
Backend (FastAPI in Python): Runs the scheduled cron jobs to pull new API data, feeds that data through your ML pipeline, updates the database, and serves data to the app.
Frontend (React Native or Flutter): The mobile app. It uses Mapbox GL JS to display a dark-mode map of the region, pulling the hex grid colors from your FastAPI backend.
Alerting (Firebase Cloud Messaging): When the backend upgrades a hex to Red, FCM pushes the AI-generated notification directly to the user's phone based on their current GPS location.

