package com.polyeats.review;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;

import org.eclipse.microprofile.rest.client.annotation.RegisterClientHeaders;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

@Path("/users")
@RegisterRestClient(configKey = "user")
@RegisterClientHeaders
public interface UserClient {

    @GET
    @Path("/{id}")
    void byId(@PathParam("id") String id);
}
