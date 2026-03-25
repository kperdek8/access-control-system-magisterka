from fastapi import FastAPI

app = FastAPI()

@app.get("/decision")
def read_root():
    return {"status": "alive", "service": "policy_decision_point"}

@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_decision_point"}