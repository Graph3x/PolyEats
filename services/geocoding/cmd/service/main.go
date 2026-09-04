package main

import (
	"context"
	"encoding/json"
	"log"
	"net"
	"net/http"

	pb "geocoding/proto"

	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"google.golang.org/grpc"
)

const defaultMessage = "hello from geocoding"

type geocodingServer struct {
	pb.UnimplementedGeocodingServer
}

func (s *geocodingServer) Hello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloResponse, error) {
	return &pb.HelloResponse{Message: defaultMessage}, nil
}

func helloHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"message": defaultMessage})
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
	mux.HandleFunc("/hello", helloHandler)
	log.Println("http listening on :8080")
	if err := http.ListenAndServe(":8080", otelhttp.NewHandler(mux, "geocoding")); err != nil {
		log.Fatalf("http serve: %v", err)
	}
}
