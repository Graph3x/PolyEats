package com.polyeats.address;

import io.grpc.CallOptions;
import io.grpc.Channel;
import io.grpc.ClientCall;
import io.grpc.ForwardingClientCall;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.Metadata;
import io.grpc.MethodDescriptor;
import jakarta.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

@Component
class GrpcChannels {

    private static final Metadata.Key<String> AUTHORIZATION =
            Metadata.Key.of("authorization", Metadata.ASCII_STRING_MARSHALLER);

    private final List<ManagedChannel> channels = new ArrayList<>();

    ManagedChannel create(String target) {
        ManagedChannel channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext()
                .intercept(GrpcChannels::forwardBearerToken)
                .build();
        channels.add(channel);
        return channel;
    }

    private static <ReqT, RespT> ClientCall<ReqT, RespT> forwardBearerToken(
            MethodDescriptor<ReqT, RespT> method, CallOptions options, Channel next) {
        return new ForwardingClientCall.SimpleForwardingClientCall<>(next.newCall(method, options)) {
            @Override
            public void start(Listener<RespT> listener, Metadata headers) {
                if (SecurityContextHolder.getContext().getAuthentication() instanceof JwtAuthenticationToken jwt) {
                    headers.put(AUTHORIZATION, "Bearer " + jwt.getToken().getTokenValue());
                }
                super.start(listener, headers);
            }
        };
    }

    @PreDestroy
    void shutdown() {
        channels.forEach(ManagedChannel::shutdown);
    }
}
