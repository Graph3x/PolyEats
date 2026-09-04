package com.polyeats.address;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import jakarta.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;

@Component
class GrpcChannels {

    private final List<ManagedChannel> channels = new ArrayList<>();

    ManagedChannel create(String target) {
        ManagedChannel channel = ManagedChannelBuilder.forTarget(target).usePlaintext().build();
        channels.add(channel);
        return channel;
    }

    @PreDestroy
    void shutdown() {
        channels.forEach(ManagedChannel::shutdown);
    }
}
