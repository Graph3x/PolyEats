package com.polyeats.address;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
class GrpcConfig {

    @Bean(destroyMethod = "shutdown")
    ManagedChannel geocodingChannel(@Value("${geocoding.address}") String address) {
        return ManagedChannelBuilder.forTarget(address).usePlaintext().build();
    }
}
