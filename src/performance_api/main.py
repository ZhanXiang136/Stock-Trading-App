from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .performance import get_performance

app = FastAPI()

# Allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/performance")
def performance():
    return get_performance()
