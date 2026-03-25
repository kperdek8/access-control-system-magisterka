from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_information_point"}