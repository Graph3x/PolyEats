package main

import (
	"context"
	"log"
	"net"
	"net/http"

	pb "geocoding/proto"

	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type geocodingServer struct {
	pb.UnimplementedGeocodingServer
}

func (s *geocodingServer) Geocode(ctx context.Context, req *pb.GeocodeRequest) (*pb.GeocodeResponse, error) {
	return nil, status.Error(codes.Unimplemented, "geocode")
}

func (s *geocodingServer) ReverseGeocode(ctx context.Context, req *pb.ReverseGeocodeRequest) (*pb.ReverseGeocodeResponse, error) {
	return nil, status.Error(codes.Unimplemented, "reverse geocode")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}

func main() {
	ctx := context.Background()
	shutdown, err := initTracing(ctx)
	if err != nil {
		log.Fatalf("tracing: %v", err)
	}
	defer shutdown(ctx)

	go func() {
		lis, err := net.Listen("tcp", ":9090")
		if err != nil {
			log.Fatalf("grpc listen: %v", err)
		}
		s := grpc.NewServer(grpc.StatsHandler(otelgrpc.NewServerHandler()))
		pb.RegisterGeocodingServer(s, &geocodingServer{})
		log.Println("grpc listening on :9090")
		if err := s.Serve(lis); err != nil {
			log.Fatalf("grpc serve: %v", err)
		}
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	log.Println("http listening on :8080")
	if err := http.ListenAndServe(":8080", otelhttp.NewHandler(mux, "geocoding")); err != nil {
		log.Fatalf("http serve: %v", err)
	}
}
