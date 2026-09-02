package com.polyeats.address;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class HelloController {

    private final GeocodingClient geocoding;

    HelloController(GeocodingClient geocoding) {
        this.geocoding = geocoding;
    }

    @GetMapping("/hello")
    Map<String, String> hello() {
        return Map.of("message", "hello from address");
    }

    @GetMapping("/hello/geocoding")
    Map<String, String> helloGeocoding() {
        return Map.of("message", geocoding.hello());
    }
}
