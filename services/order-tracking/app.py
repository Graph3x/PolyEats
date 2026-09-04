import os

import geocoding_pb2
import geocoding_pb2_grpc
import uvicorn
from clients import grpc_channel
from fastapi import FastAPI, Response

TIMEOUT = 5.0

app = FastAPI()
geocoding = geocoding_pb2_grpc.GeocodingStub(grpc_channel(os.environ["GEOCODING_ADDR"]))


@app.get("/health")
def health():
    return Response(status_code=200)


@app.get("/test")
def test():
    request = geocoding_pb2.ReverseGeocodeRequest(
        coordinates=geocoding_pb2.Coordinates(lat=49.7175, lon=14.4661)
    )
    address = geocoding.ReverseGeocode(request, timeout=TIMEOUT).address
    return {
        "street": address.street,
        "building_number": address.building_number,
        "city": address.city,
        "postal_code": address.postal_code,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
