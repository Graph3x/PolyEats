# Dockerfile template — Java / Quarkus services.

ARG MAVEN_VERSION=3.9
ARG JAVA_VERSION=25

FROM maven:${MAVEN_VERSION}-eclipse-temurin-${JAVA_VERSION} AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B package -DskipTests -Dquarkus.package.jar.type=fast-jar

FROM eclipse-temurin:${JAVA_VERSION}-jre-alpine
COPY --from=build /src/target/quarkus-app/ /app/
ENTRYPOINT ["java", "-jar", "/app/quarkus-run.jar"]
