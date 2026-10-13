# Dockerfile — geocoding. Go template plus a sqlite seed stage.

ARG GO_VERSION=1.27.0
ARG ALPINE_VERSION=3.24

FROM golang:${GO_VERSION}-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /service ./cmd/service

FROM golang:${GO_VERSION}-alpine AS seed
RUN apk add --no-cache sqlite
COPY db/geo.sql /geo.sql
RUN sqlite3 /geo.db < /geo.sql

FROM alpine:${ALPINE_VERSION}
COPY --from=build /service /service
COPY --from=seed /geo.db /data/geo.db
ENTRYPOINT ["/service"]
