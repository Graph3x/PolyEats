package main

import (
	"context"
	"database/sql"
	"errors"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	pb "geocoding/proto"

	"github.com/XSAM/otelsql"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	_ "modernc.org/sqlite"
)

type geocodingServer struct {
	pb.UnimplementedGeocodingServer
	db *sql.DB
}

func (s *geocodingServer) Geocode(ctx context.Context, req *pb.GeocodeRequest) (*pb.GeocodeResponse, error) {
	address := req.GetAddress()

	var lat, lon float64
	err := s.db.QueryRowContext(ctx,
		"SELECT lat, lon FROM addresses WHERE city = ? AND street = ? AND building_number = ?",
		address.GetCity(), address.GetStreet(), address.GetBuildingNumber(),
	).Scan(&lat, &lon)

	if errors.Is(err, sql.ErrNoRows) {
		return nil, status.Error(codes.NotFound, "address not found")
	}
	if err != nil {
		return nil, status.Error(codes.Internal, "lookup failed")
	}

	return &pb.GeocodeResponse{Coordinates: &pb.Coordinates{Lat: lat, Lon: lon}}, nil
}

func (s *geocodingServer) ReverseGeocode(ctx context.Context, req *pb.ReverseGeocodeRequest) (*pb.ReverseGeocodeResponse, error) {
	coordinates := req.GetCoordinates()

	var street, buildingNumber, city, postalCode string
	err := s.db.QueryRowContext(ctx,
		"SELECT street, building_number, city, postal_code FROM addresses "+
			"ORDER BY (lat - ?) * (lat - ?) + (lon - ?) * (lon - ?) LIMIT 1",
		coordinates.GetLat(), coordinates.GetLat(), coordinates.GetLon(), coordinates.GetLon(),
	).Scan(&street, &buildingNumber, &city, &postalCode)

	if errors.Is(err, sql.ErrNoRows) {
		return nil, status.Error(codes.NotFound, "no address near coordinates")
	}
	if err != nil {
		return nil, status.Error(codes.Internal, "lookup failed")
	}

	return &pb.ReverseGeocodeResponse{Address: &pb.Address{
		Street:         street,
		BuildingNumber: buildingNumber,
		City:           city,
		PostalCode:     postalCode,
	}}, nil
}

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

	db, err := otelsql.Open("sqlite", "file:"+os.Getenv("GEO_DB_PATH")+"?mode=ro",
		otelsql.WithAttributes(attribute.String("db.system", "sqlite")))
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	if err := db.Ping(); err != nil {
		log.Fatalf("ping db: %v", err)
	}

	lis, err := net.Listen("tcp", ":9090")
	if err != nil {
		log.Fatalf("grpc listen: %v", err)
	}

	grpcServer := grpc.NewServer(grpc.StatsHandler(otelgrpc.NewServerHandler()))
	pb.RegisterGeocodingServer(grpcServer, &geocodingServer{db: db})

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	httpServer := &http.Server{Addr: ":8080", Handler: otelhttp.NewHandler(mux, "geocoding")}

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
	db.Close()
	shutdown(shutdownCtx)
}
