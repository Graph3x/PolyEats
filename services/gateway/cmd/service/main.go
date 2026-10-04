package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	pb "gateway/proto"

	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	shutdown, err := initTracing(ctx)
	if err != nil {
		log.Fatalf("tracing: %v", err)
	}

	authConn, err := grpc.NewClient(os.Getenv("AUTH_ADDR"),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithStatsHandler(otelgrpc.NewClientHandler()))
	if err != nil {
		log.Fatalf("auth client: %v", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	registerAuth(mux, pb.NewAuthClient(authConn))
	if err := registerRoutes(mux, newVerifier(os.Getenv("JWKS_URL"))); err != nil {
		log.Fatalf("routes: %v", err)
	}
	httpServer := &http.Server{Addr: ":8080", Handler: otelhttp.NewHandler(mux, "gateway")}

	serveErr := make(chan error, 1)
	go func() {
		log.Println("http listening on :8080")
		serveErr <- httpServer.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
	case err := <-serveErr:
		log.Printf("serve: %v", err)
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	httpServer.Shutdown(shutdownCtx)
	authConn.Close()
	shutdown(shutdownCtx)
}
