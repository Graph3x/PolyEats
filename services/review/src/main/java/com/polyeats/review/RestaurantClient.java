package com.polyeats.review;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import org.eclipse.microprofile.rest.client.annotation.RegisterClientHeaders;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

@Path("/restaurants")
@RegisterRestClient(configKey = "restaurant")
@RegisterClientHeaders
public interface RestaurantClient {

    @GET
    @Path("/{id}")
    void byId(@PathParam("id") String id);
}
