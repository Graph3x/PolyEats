package com.polyeats.restaurant;

import org.springframework.boot.restclient.RestTemplateBuilder;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

@Component
class MenuClient {

    private final RestTemplate rest;

    MenuClient(RestTemplateBuilder builder) {
        this.rest =
                builder.connectTimeout(Duration.ofSeconds(2))
                        .readTimeout(Duration.ofSeconds(5))
                        .additionalInterceptors((request, body, execution) -> {
                            if (SecurityContextHolder.getContext().getAuthentication()
                                    instanceof JwtAuthenticationToken jwt) {
                                request.getHeaders().setBearerAuth(jwt.getToken().getTokenValue());
                            }
                            return execution.execute(request, body);
                        })
                        .build();
    }

    void deleteByRestaurant(String restaurantId) {
        rest.delete("http://menu:8080/items?restaurantId={id}", restaurantId);
    }
}
