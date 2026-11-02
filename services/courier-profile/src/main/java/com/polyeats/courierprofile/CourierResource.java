package com.polyeats.courierprofile;

import io.quarkus.security.Authenticated;

import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.DELETE;
import jakarta.ws.rs.ForbiddenException;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.core.Response;

import org.eclipse.microprofile.jwt.JsonWebToken;
import org.hibernate.exception.ConstraintViolationException;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

@Path("/couriers")
@Authenticated
public class CourierResource {

    public record NewStatus(String status) {}

    @Inject JsonWebToken jwt;

    @POST
    @Transactional
    public Courier create(Courier courier) {
        courier.accountId = jwt.getSubject();
        courier.persistAndFlush();
        return courier;
    }

    @GET
    @Path("/{id}")
    public Courier byId(@PathParam("id") String id) {
        return Courier.<Courier>findByIdOptional(id).orElseThrow(NotFoundException::new);
    }

    @PUT
    @Path("/{id}")
    @Transactional
    public Courier update(@PathParam("id") String id, Courier courier) {
        requireOwner(id);
        Courier stored = byId(id);
        stored.name = courier.name;
        stored.vehicle = courier.vehicle;
        stored.status = courier.status;
        Courier.flush();
        return stored;
    }

    @PUT
    @Path("/{id}/status")
    @Transactional
    public Courier updateStatus(@PathParam("id") String id, NewStatus status) {
        requireOwner(id);
        Courier stored = byId(id);
        stored.status = status.status();
        Courier.flush();
        return stored;
    }

    @DELETE
    @Path("/{id}")
    @Transactional
    public void delete(@PathParam("id") String id) {
        requireOwner(id);
        Courier.deleteById(id);
    }

    private void requireOwner(String id) {
        if (!id.equals(jwt.getSubject())) {
            throw new ForbiddenException();
        }
    }

    @ServerExceptionMapper
    public Response invalidCourier(ConstraintViolationException e) {
        return Response.status("23505".equals(e.getSQLState()) ? 409 : 400).build();
    }
}
