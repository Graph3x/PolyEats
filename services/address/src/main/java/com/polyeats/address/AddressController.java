package com.polyeats.address;

import com.polyeats.geocoding.Coordinates;
import com.polyeats.geocoding.GeocodeRequest;
import com.polyeats.geocoding.GeocodingGrpc;
import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import java.util.List;
import java.util.concurrent.TimeUnit;
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
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
class AddressController {

    record Address(Long id, String ownerType, String ownerId, String street,
                   String buildingNumber, String city, String postalCode,
                   Double lat, Double lon) {
    }

    private final JdbcTemplate jdbc;
    private final GeocodingGrpc.GeocodingBlockingStub geocoding;

    AddressController(JdbcTemplate jdbc, GrpcChannels channels) {
        this.jdbc = jdbc;
        this.geocoding = GeocodingGrpc.newBlockingStub(channels.create("geocoding:9090"));
    }

    @GetMapping("/health")
    void health() {
    }

    @PostMapping("/addresses")
    Address create(@RequestBody Address address) {
        Coordinates coordinates = resolve(address);
        Long id = jdbc.queryForObject(
                "INSERT INTO addresses (owner_type, owner_id, street, building_number, city, postal_code, lat, lon) "
                        + "VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
                Long.class,
                address.ownerType(), address.ownerId(), address.street(), address.buildingNumber(),
                address.city(), address.postalCode(), coordinates.getLat(), coordinates.getLon());
        return byId(id);
    }

    @GetMapping("/addresses/{id}")
    Address byId(@PathVariable Long id) {
        return jdbc.queryForObject("SELECT * FROM addresses WHERE id = ?",
                new DataClassRowMapper<>(Address.class), id);
    }

    @GetMapping("/addresses")
    List<Address> byOwner(@RequestParam String ownerType, @RequestParam String ownerId) {
        return jdbc.query("SELECT * FROM addresses WHERE owner_type = ? AND owner_id = ?",
                new DataClassRowMapper<>(Address.class), ownerType, ownerId);
    }

    @PutMapping("/addresses/{id}")
    Address update(@PathVariable Long id, @RequestBody Address address) {
        Coordinates coordinates = resolve(address);
        jdbc.update(
                "UPDATE addresses SET owner_type = ?, owner_id = ?, street = ?, building_number = ?, "
                        + "city = ?, postal_code = ?, lat = ?, lon = ? WHERE id = ?",
                address.ownerType(), address.ownerId(), address.street(), address.buildingNumber(),
                address.city(), address.postalCode(), coordinates.getLat(), coordinates.getLon(), id);
        return byId(id);
    }

    @DeleteMapping("/addresses/{id}")
    void delete(@PathVariable Long id) {
        jdbc.update("DELETE FROM addresses WHERE id = ?", id);
    }

    @ExceptionHandler(EmptyResultDataAccessException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    void addressNotFound() {
    }

    @ExceptionHandler(StatusRuntimeException.class)
    ResponseEntity<Void> geocodingFailed(StatusRuntimeException e) {
        return ResponseEntity.status(e.getStatus().getCode() == Status.Code.NOT_FOUND
                ? HttpStatus.UNPROCESSABLE_ENTITY
                : HttpStatus.BAD_GATEWAY).build();
    }

    private Coordinates resolve(Address address) {
        return geocoding.withDeadlineAfter(5, TimeUnit.SECONDS)
                .geocode(GeocodeRequest.newBuilder()
                        .setAddress(com.polyeats.geocoding.Address.newBuilder()
                                .setStreet(address.street())
                                .setBuildingNumber(address.buildingNumber())
                                .setCity(address.city())
                                .setPostalCode(address.postalCode())
                                .build())
                        .build())
                .getCoordinates();
    }
}
