package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
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

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	if err := registerRoutes(mux); err != nil {
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
	shutdown(shutdownCtx)
}
