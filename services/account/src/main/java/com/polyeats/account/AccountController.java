package com.polyeats.account;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.DataClassRowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
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
class AccountController {

    record Credentials(String email, String password) {
    }

    record NewPassword(String password) {
    }

    record Identity(String accountId, String role, long epoch) {
    }

    record State(String role, long epoch) {
    }

    record Stored(String accountId, String passwordHash, String role, long epoch) {
    }

    private final JdbcTemplate jdbc;
    private final ProfileClient profiles;
    private final PasswordEncoder passwords = new BCryptPasswordEncoder();

    AccountController(JdbcTemplate jdbc, ProfileClient profiles) {
        this.jdbc = jdbc;
        this.profiles = profiles;
    }

    @GetMapping("/health")
    void health() {
    }

    @PostMapping("/accounts")
    Identity register(@RequestBody Credentials credentials) {
        return jdbc.queryForObject(
                "INSERT INTO accounts (email, password_hash) VALUES (?, ?) RETURNING account_id, role, epoch",
                new DataClassRowMapper<>(Identity.class),
                credentials.email(), passwords.encode(credentials.password()));
    }

    @PutMapping("/accounts/{id}/password")
    void changePassword(@AuthenticationPrincipal Jwt jwt, @PathVariable String id, @RequestBody NewPassword password) {
        requireOwner(jwt, id);
        jdbc.update("UPDATE accounts SET password_hash = ?, epoch = epoch + 1 WHERE account_id = ?",
                passwords.encode(password.password()), id);
    }

    @DeleteMapping("/accounts/{id}")
    void delete(@AuthenticationPrincipal Jwt jwt, @PathVariable String id) {
        requireOwner(jwt, id);
        profiles.deleteAll(id);
        jdbc.update("DELETE FROM accounts WHERE account_id = ?", id);
    }

    @PostMapping("/accounts/verify")
    Identity verify(@RequestBody Credentials credentials) {
        return jdbc.query("SELECT account_id, password_hash, role, epoch FROM accounts WHERE email = ?",
                        new DataClassRowMapper<>(Stored.class), credentials.email())
                .stream()
                .filter(stored -> passwords.matches(credentials.password(), stored.passwordHash()))
                .map(stored -> new Identity(stored.accountId(), stored.role(), stored.epoch()))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
    }

    @GetMapping("/accounts/{id}/state")
    State state(@PathVariable String id) {
        return jdbc.queryForObject("SELECT role, epoch FROM accounts WHERE account_id = ?",
                new DataClassRowMapper<>(State.class), id);
    }

    private static void requireOwner(Jwt jwt, String id) {
        if (!id.equals(jwt.getSubject())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN);
        }
    }

    @ExceptionHandler(EmptyResultDataAccessException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    void accountNotFound() {
    }

    @ExceptionHandler(DuplicateKeyException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    void alreadyExists() {
    }

    @ExceptionHandler({DataIntegrityViolationException.class, IllegalArgumentException.class})
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    void invalidAccount() {
    }

    @ExceptionHandler(RestClientException.class)
    ResponseEntity<Void> profileFailed(RestClientException e) {
        boolean timedOut = e.getCause() instanceof SocketTimeoutException || e.getCause() instanceof HttpTimeoutException;
        return ResponseEntity.status(timedOut ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY).build();
    }
}
