web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 75 --workers 2
worker: python run_grant_search.py
release: alembic upgrade head
