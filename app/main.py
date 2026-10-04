from fastapi import FastAPI
import os

app=FastAPI(title="k8s-fastapi", version="0.1.0")

@app.get("/")
def root():
    return {"message": "hello", "version": os.getenv("APP_VERSION", "v1")}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"status": "ready"}
