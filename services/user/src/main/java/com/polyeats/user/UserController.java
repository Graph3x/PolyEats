package com.polyeats.user;

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

@RestController
class UserController {

    record User(Long id, String name, String email) {
    }

    private final JdbcTemplate jdbc;
    private final AddressClient addresses;

    UserController(JdbcTemplate jdbc, AddressClient addresses) {
        this.jdbc = jdbc;
        this.addresses = addresses;
    }

    @GetMapping("/health")
    void health() {
    }

    @PostMapping("/users")
    User create(@RequestBody User user) {
        Long id = jdbc.queryForObject("INSERT INTO users (name, email) VALUES (?, ?) RETURNING id",
                Long.class, user.name(), user.email());
        return byId(id);
    }

    @GetMapping("/users/{id}")
    User byId(@PathVariable Long id) {
        return jdbc.queryForObject("SELECT * FROM users WHERE id = ?",
                new DataClassRowMapper<>(User.class), id);
    }

    @PutMapping("/users/{id}")
    User update(@PathVariable Long id, @RequestBody User user) {
        byId(id);
        jdbc.update("UPDATE users SET name = ?, email = ? WHERE id = ?", user.name(), user.email(), id);
        return byId(id);
    }

    @GetMapping("/users/{id}/addresses")
    List<AddressClient.Address> addresses(@PathVariable Long id) {
        byId(id);
        return addresses.byUser(id);
    }

    @DeleteMapping("/users/{id}")
    void delete(@PathVariable Long id) {
        jdbc.update("DELETE FROM users WHERE id = ?", id);
    }

    @ExceptionHandler(EmptyResultDataAccessException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    void userNotFound() {
    }

    @ExceptionHandler(DuplicateKeyException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    void emailTaken() {
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    void invalidUser() {
    }

    @ExceptionHandler(RestClientException.class)
    ResponseEntity<Void> addressFailed(RestClientException e) {
        boolean timedOut = e.getCause() instanceof SocketTimeoutException || e.getCause() instanceof HttpTimeoutException;
        return ResponseEntity.status(timedOut ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY).build();
    }
}
