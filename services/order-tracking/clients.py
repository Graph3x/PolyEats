import os

import geocoding_pb2
import geocoding_pb2_grpc
import grpc

TIMEOUT = 5.0


class GeocodingClient:
    def __init__(self, addr):
        self._channel = grpc.insecure_channel(addr)
        self._stub = geocoding_pb2_grpc.GeocodingStub(self._channel)

    def hello(self):
        return self._stub.Hello(geocoding_pb2.HelloRequest(), timeout=TIMEOUT).message


geocoding = GeocodingClient(os.environ["GEOCODING_ADDR"])
