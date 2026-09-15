import os

import geocoding_pb2
import geocoding_pb2_grpc
import uvicorn
from clients import grpc_channel
from fastapi import FastAPI, Response

TIMEOUT = 5.0

# Stands in for a live position until courier-location exists.
COURIER_POSITION = (49.7175, 14.4661)

app = FastAPI()
geocoding = geocoding_pb2_grpc.GeocodingStub(grpc_channel(os.environ["GEOCODING_ADDR"]))


@app.get("/health")
def health():
    return Response(status_code=200)


@app.get("/tracking/{order_id}")
def tracking(order_id: str):
    latitude, longitude = COURIER_POSITION
    request = geocoding_pb2.ReverseGeocodeRequest(
        coordinates=geocoding_pb2.Coordinates(lat=latitude, lon=longitude)
    )
    address = geocoding.ReverseGeocode(request, timeout=TIMEOUT).address
    return {
        "orderId": order_id,
        "courierLocation": {
            "street": address.street,
            "buildingNumber": address.building_number,
            "city": address.city,
            "postalCode": address.postal_code,
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
