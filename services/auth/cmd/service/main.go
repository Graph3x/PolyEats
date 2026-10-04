package main

import (
	"context"
	"crypto/rand"
	"errors"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
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

var errUnauthenticated = status.Error(codes.Unauthenticated, "invalid credentials or token")

func unavailable(err error) error {
	log.Printf("unavailable: %v", err)
	return status.Error(codes.Unavailable, "dependency unavailable")
}

func (s *authServer) Login(ctx context.Context, req *pb.LoginRequest) (*pb.TokenPair, error) {
	identity, err := s.verifyCredentials(ctx, req.Email, req.Password)
	if errors.Is(err, errInvalidCredentials) {
		return nil, errUnauthenticated
	}
	if err != nil {
		return nil, unavailable(err)
	}

	familyID, secret := rand.Text(), rand.Text()
	sess := session{AccountID: identity.AccountID, Epoch: identity.Epoch, Hash: hashSecret(secret)}
	if err := s.createSession(ctx, familyID, sess); err != nil {
		return nil, unavailable(err)
	}
	return s.tokenPair(identity.AccountID, identity.Role, familyID, secret)
}

func (s *authServer) Refresh(ctx context.Context, req *pb.RefreshRequest) (*pb.TokenPair, error) {
	familyID, secret, ok := strings.Cut(req.RefreshToken, ".")
	if !ok {
		return nil, errUnauthenticated
	}
	sess, err := getSession(ctx, s.store, familyID)
	if errors.Is(err, errSessionNotFound) {
		return nil, errUnauthenticated
	}
	if err != nil {
		return nil, unavailable(err)
	}
	if sess.Hash != hashSecret(secret) {
		return nil, s.revoke(ctx, familyID)
	}

	state, err := s.getAccountState(ctx, sess.AccountID)
	if errors.Is(err, errAccountNotFound) || (err == nil && state.Epoch != sess.Epoch) {
		return nil, s.revoke(ctx, familyID)
	}
	if err != nil {
		return nil, unavailable(err)
	}

	newSecret := rand.Text()
	err = s.rotateSession(ctx, familyID, sess.Hash, hashSecret(newSecret))
	if errors.Is(err, errTokenReused) {
		return nil, s.revoke(ctx, familyID)
	}
	if errors.Is(err, errSessionNotFound) {
		return nil, errUnauthenticated
	}
	if err != nil {
		return nil, unavailable(err)
	}
	return s.tokenPair(sess.AccountID, state.Role, familyID, newSecret)
}

func (s *authServer) Logout(ctx context.Context, req *pb.LogoutRequest) (*pb.LogoutResponse, error) {
	familyID, _, ok := strings.Cut(req.RefreshToken, ".")
	if !ok {
		return &pb.LogoutResponse{}, nil
	}
	if err := s.deleteSession(ctx, familyID); err != nil {
		return nil, unavailable(err)
	}
	return &pb.LogoutResponse{}, nil
}

func (s *authServer) revoke(ctx context.Context, familyID string) error {
	if err := s.deleteSession(ctx, familyID); err != nil {
		return unavailable(err)
	}
	return errUnauthenticated
}

func (s *authServer) tokenPair(accountID, role, familyID, secret string) (*pb.TokenPair, error) {
	access, err := s.keys.issueAccessToken(accountID, role)
	if err != nil {
		return nil, status.Error(codes.Internal, "sign access token")
	}
	return &pb.TokenPair{
		AccessToken:  access,
		RefreshToken: familyID + "." + secret,
		ExpiresIn:    int32(accessTokenTTL.Seconds()),
	}, nil
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
