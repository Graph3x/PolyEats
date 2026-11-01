package com.polyeats.review;

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
import jakarta.ws.rs.ProcessingException;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.Response;
import java.util.List;
import org.eclipse.microprofile.jwt.JsonWebToken;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.hibernate.exception.ConstraintViolationException;
import org.jboss.resteasy.reactive.ClientWebApplicationException;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

@Path("/reviews")
@Authenticated
public class ReviewResource {

    @Inject
    JsonWebToken jwt;

    @Inject
    @RestClient
    RestaurantClient restaurants;

    @Inject
    @RestClient
    UserClient users;

    @POST
    @Transactional
    public Review create(Review review) {
        review.id = null;
        review.authorId = jwt.getSubject();
        restaurants.byId(review.restaurantId);
        users.byId(review.authorId);
        review.persistAndFlush();
        return review;
    }

    @GET
    public List<Review> byRestaurant(@QueryParam("restaurantId") String restaurantId) {
        return Review.list("restaurantId", restaurantId);
    }

    @GET
    @Path("/{id}")
    public Review byId(@PathParam("id") Long id) {
        return Review.<Review>findByIdOptional(id).orElseThrow(NotFoundException::new);
    }

    @PUT
    @Path("/{id}")
    @Transactional
    public Review update(@PathParam("id") Long id, Review review) {
        Review stored = byId(id);
        requireAuthor(stored);
        stored.rating = review.rating;
        stored.text = review.text;
        Review.flush();
        return stored;
    }

    @DELETE
    @Path("/{id}")
    @Transactional
    public void delete(@PathParam("id") Long id) {
        Review stored = byId(id);
        requireAuthor(stored);
        stored.delete();
    }

    private void requireAuthor(Review review) {
        if (!review.authorId.equals(jwt.getSubject())) {
            throw new ForbiddenException();
        }
    }

    @ServerExceptionMapper
    public Response invalidReview(ConstraintViolationException e) {
        return Response.status("23505".equals(e.getSQLState()) ? 409 : 400).build();
    }

    @ServerExceptionMapper
    public Response dependencyRejected(ClientWebApplicationException e) {
        return Response.status(e.getResponse().getStatus() == 404 ? 422 : 502).build();
    }

    @ServerExceptionMapper
    public Response dependencyUnavailable(ProcessingException e) {
        return Response.status(502).build();
    }
}
