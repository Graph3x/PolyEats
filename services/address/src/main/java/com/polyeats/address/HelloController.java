package com.polyeats.address;

import com.polyeats.geocoding.GeocodingGrpc;
import com.polyeats.geocoding.HelloRequest;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class HelloController {

    private final GeocodingGrpc.GeocodingBlockingStub geocoding;

    HelloController(GrpcChannels channels) {
        this.geocoding = GeocodingGrpc.newBlockingStub(channels.create("geocoding:9090"));
    }

    @GetMapping("/hello")
    Map<String, String> hello() {
        return Map.of("message", "hello from address");
    }

    @GetMapping("/hello/geocoding")
    Map<String, String> helloGeocoding() {
        String message = geocoding.withDeadlineAfter(5, TimeUnit.SECONDS)
                .hello(HelloRequest.getDefaultInstance())
                .getMessage();
        return Map.of("message", message);
    }
}
