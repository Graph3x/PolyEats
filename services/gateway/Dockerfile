# Dockerfile — gateway. Go template.

ARG GO_VERSION=1.27.0
ARG ALPINE_VERSION=3.24

FROM golang:${GO_VERSION}-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /service ./cmd/service

FROM alpine:${ALPINE_VERSION}
COPY --from=build /service /service
ENTRYPOINT ["/service"]
