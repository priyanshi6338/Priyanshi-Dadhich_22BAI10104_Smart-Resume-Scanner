Smart Resume Scanner - Enhanced
- backend: Flask + SQLite + background worker (no external queue required)
- frontend: React (Vite)

Setup:
1) Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   cp .env.example .env  # add OPENAI_API_KEY if you want LLM/embeddings
   python app.py
   The backend runs on http://localhost:5000

2) Frontend (dev)
   cd frontend
   npm install
   npm run dev
   - OR build: npm run build  (outputs dist/) and the backend can serve the built files.

Notes:
- The background worker runs as a daemon thread inside the Flask process and processes queued matches.
- This is a simple local setup suitable for demos. For production, replace background worker with a proper task queue (RQ/Celery) and use PostgreSQL.
