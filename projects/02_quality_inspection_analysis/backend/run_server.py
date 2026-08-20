import uvicorn
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == '__main__':
    print("Starting FastAPI server on http://127.0.0.1:8000...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
