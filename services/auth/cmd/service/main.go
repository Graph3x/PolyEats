package main

import (
	"context"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	pb "auth/proto"

	"github.com/valkey-io/valkey-go"
	"github.com/valkey-io/valkey-go/valkeyotel"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type authServer struct {
	pb.UnimplementedAuthServer
	keys       *keySet
	store      valkey.Client
	account    *http.Client
	accountURL string
}

func (s *authServer) Login(ctx context.Context, req *pb.LoginRequest) (*pb.TokenPair, error) {
	return nil, status.Error(codes.Unimplemented, "not implemented")
}

func (s *authServer) Refresh(ctx context.Context, req *pb.RefreshRequest) (*pb.TokenPair, error) {
	return nil, status.Error(codes.Unimplemented, "not implemented")
}

func (s *authServer) Logout(ctx context.Context, req *pb.LogoutRequest) (*pb.LogoutResponse, error) {
	return nil, status.Error(codes.Unimplemented, "not implemented")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}

func jwksHandler(body []byte) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(body)
	}
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	shutdown, err := initTracing(ctx)
	if err != nil {
		log.Fatalf("tracing: %v", err)
	}

	keys, err := loadKeySet(os.Getenv("JWT_KEY_PATH"))
	if err != nil {
		log.Fatalf("load signing key: %v", err)
	}
	jwks, err := keys.jwks()
	if err != nil {
		log.Fatalf("build jwks: %v", err)
	}

	store, err := valkeyotel.NewClient(valkey.ClientOption{InitAddress: []string{os.Getenv("VALKEY_ADDR")}})
	if err != nil {
		log.Fatalf("connect valkey: %v", err)
	}

	account := &http.Client{
		Timeout:   5 * time.Second,
		Transport: otelhttp.NewTransport(http.DefaultTransport),
	}

	lis, err := net.Listen("tcp", ":9090")
	if err != nil {
		log.Fatalf("grpc listen: %v", err)
	}

	grpcServer := grpc.NewServer(grpc.StatsHandler(otelgrpc.NewServerHandler()))
	pb.RegisterAuthServer(grpcServer, &authServer{
		keys:       keys,
		store:      store,
		account:    account,
		accountURL: os.Getenv("ACCOUNT_URL"),
	})

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("GET /.well-known/jwks.json", jwksHandler(jwks))
	httpServer := &http.Server{Addr: ":8080", Handler: otelhttp.NewHandler(mux, "auth")}

	serveErr := make(chan error, 2)
	go func() {
		log.Println("grpc listening on :9090")
		serveErr <- grpcServer.Serve(lis)
	}()
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

	grpcServer.GracefulStop()
	httpServer.Shutdown(shutdownCtx)
	store.Close()
	shutdown(shutdownCtx)
}
