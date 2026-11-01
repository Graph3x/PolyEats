package com.polyeats.account;

import java.time.Duration;
import java.util.List;
import org.springframework.boot.restclient.RestTemplateBuilder;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
class ProfileClient {

    private static final List<String> PROFILES = List.of(
            "http://user:8080/users/{id}",
            "http://restaurant:8080/restaurants/{id}",
            "http://courier-profile:8080/couriers/{id}");

    private final RestTemplate rest;

    ProfileClient(RestTemplateBuilder builder) {
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

    void deleteAll(String accountId) {
        PROFILES.forEach(url -> rest.delete(url, accountId));
    }
}
