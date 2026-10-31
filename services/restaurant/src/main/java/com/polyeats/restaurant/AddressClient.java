package com.polyeats.restaurant;

import java.time.Duration;
import java.util.List;
import org.springframework.boot.restclient.RestTemplateBuilder;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
class AddressClient {

    record Address(Long id, String ownerType, String ownerId, String street,
                   String buildingNumber, String city, String postalCode,
                   Double lat, Double lon) {
    }

    private final RestTemplate rest;

    AddressClient(RestTemplateBuilder builder) {
        this.rest = builder
                .connectTimeout(Duration.ofSeconds(2))
                .readTimeout(Duration.ofSeconds(5))
                .additionalInterceptors((request, body, execution) -> {
                    if (SecurityContextHolder.getContext().getAuthentication() instanceof JwtAuthenticationToken jwt) {
                        request.getHeaders().setBearerAuth(jwt.getToken().getTokenValue());
                    }
                    return execution.execute(request, body);
                })
                .build();
    }

    List<Address> byRestaurant(String restaurantId) {
        return List.of(rest.getForObject("http://address:8080/addresses?ownerType=restaurant&ownerId={id}", Address[].class, restaurantId));
    }
}
