package com.polyeats.restaurant;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.util.List;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.DataClassRowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@RestController
class RestaurantController {

    record Restaurant(String accountId, String name, String cuisine) {
    }

    private final JdbcTemplate jdbc;
    private final AddressClient addresses;

    RestaurantController(JdbcTemplate jdbc, AddressClient addresses) {
        this.jdbc = jdbc;
        this.addresses = addresses;
    }

    @GetMapping("/health")
    void health() {
    }

    @PostMapping("/restaurants")
    Restaurant create(@AuthenticationPrincipal Jwt jwt, @RequestBody Restaurant restaurant) {
        jdbc.update("INSERT INTO restaurants (account_id, name, cuisine) VALUES (?, ?, ?)",
                jwt.getSubject(), restaurant.name(), restaurant.cuisine());
        return byId(jwt.getSubject());
    }

    @GetMapping("/restaurants")
    List<Restaurant> all() {
        return jdbc.query("SELECT * FROM restaurants", new DataClassRowMapper<>(Restaurant.class));
    }

    @GetMapping("/restaurants/{id}")
    Restaurant byId(@PathVariable String id) {
        return jdbc.queryForObject("SELECT * FROM restaurants WHERE account_id = ?",
                new DataClassRowMapper<>(Restaurant.class), id);
    }

    @PutMapping("/restaurants/{id}")
    Restaurant update(@AuthenticationPrincipal Jwt jwt, @PathVariable String id, @RequestBody Restaurant restaurant) {
        requireOwner(jwt, id);
        byId(id);
        jdbc.update("UPDATE restaurants SET name = ?, cuisine = ? WHERE account_id = ?",
                restaurant.name(), restaurant.cuisine(), id);
        return byId(id);
    }

    @GetMapping("/restaurants/{id}/addresses")
    List<AddressClient.Address> addresses(@PathVariable String id) {
        byId(id);
        return addresses.byRestaurant(id);
    }

    @DeleteMapping("/restaurants/{id}")
    void delete(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        requireOwner(jwt, id);
        jdbc.update("DELETE FROM restaurants WHERE account_id = ?", id);
    }

    private static void requireOwner(Jwt jwt, String id) {
        if (!id.equals(jwt.getSubject())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN);
        }
    }

    @ExceptionHandler(EmptyResultDataAccessException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    void restaurantNotFound() {
    }

    @ExceptionHandler(DuplicateKeyException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    void alreadyExists() {
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    void invalidRestaurant() {
    }

    @ExceptionHandler(RestClientException.class)
    ResponseEntity<Void> addressFailed(RestClientException e) {
        boolean timedOut = e.getCause() instanceof SocketTimeoutException || e.getCause() instanceof HttpTimeoutException;
        return ResponseEntity.status(timedOut ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY).build();
    }
}
