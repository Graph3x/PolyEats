package com.polyeats.address;

import com.polyeats.geocoding.GeocodingGrpc;
import com.polyeats.geocoding.HelloRequest;
import io.grpc.ManagedChannel;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;

@Component
class GeocodingClient {

    private final GeocodingGrpc.GeocodingBlockingStub stub;

    GeocodingClient(ManagedChannel geocodingChannel) {
        this.stub = GeocodingGrpc.newBlockingStub(geocodingChannel);
    }

    String hello() {
        return stub.withDeadlineAfter(5, TimeUnit.SECONDS)
                .hello(HelloRequest.getDefaultInstance())
                .getMessage();
    }
}
