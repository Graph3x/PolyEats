package com.polyeats.user;

import java.time.Duration;
import org.springframework.boot.restclient.RestTemplateBuilder;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
class ReviewClient {

    private final RestTemplate rest;

    ReviewClient(RestTemplateBuilder builder) {
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

    void deleteByAuthor(String authorId) {
        rest.delete("http://review:8080/reviews?authorId={id}", authorId);
    }
}
