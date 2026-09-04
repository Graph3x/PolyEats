import uvicorn
from clients import geocoding
from fastapi import FastAPI, Response

app = FastAPI()


@app.get("/health")
def health():
    return Response(status_code=200)


@app.get("/hello")
def hello():
    return {"message": "hello from order-tracking"}


@app.get("/hello/geocoding")
def hello_geocoding():
    return {"message": geocoding.hello()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
