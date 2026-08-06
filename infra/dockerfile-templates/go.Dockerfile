# Dockerfile template — Go services.

ARG GO_VERSION=1.26.5

FROM golang:${GO_VERSION}-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /service ./cmd/service

FROM gcr.io/distroless/static-debian13
COPY --from=build /service /service
EXPOSE 8080
ENTRYPOINT ["/service"]
