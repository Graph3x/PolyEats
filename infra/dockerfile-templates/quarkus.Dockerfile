# Dockerfile template — Java / Quarkus services.

ARG MAVEN_VERSION=3.9
ARG JAVA_VERSION=25
ARG OTEL_JAVAAGENT_VERSION=v2.30.0

FROM maven:${MAVEN_VERSION}-eclipse-temurin-${JAVA_VERSION} AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B package -DskipTests -Dquarkus.package.jar.type=fast-jar

FROM eclipse-temurin:${JAVA_VERSION}-jre-alpine
ARG OTEL_JAVAAGENT_VERSION
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/${OTEL_JAVAAGENT_VERSION}/opentelemetry-javaagent.jar /otel/opentelemetry-javaagent.jar
COPY --from=build /src/target/quarkus-app/ /app/
ENTRYPOINT ["java", "-javaagent:/otel/opentelemetry-javaagent.jar", "-jar", "/app/quarkus-run.jar"]
