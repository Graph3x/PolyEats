package main

import (
	"context"
	"io"
	"net/http"
	"time"

	pb "gateway/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
)

const authTimeout = 5 * time.Second

var jsonOut = protojson.MarshalOptions{UseProtoNames: true, EmitUnpopulated: true}

func registerAuth(mux *http.ServeMux, auth pb.AuthClient) {
	mux.HandleFunc("POST /auth/login", authRoute(func() *pb.LoginRequest { return new(pb.LoginRequest) }, auth.Login))
	mux.HandleFunc("POST /auth/refresh", authRoute(func() *pb.RefreshRequest { return new(pb.RefreshRequest) }, auth.Refresh))
	mux.HandleFunc("POST /auth/logout", authRoute(func() *pb.LogoutRequest { return new(pb.LogoutRequest) }, auth.Logout))
}

func authRoute[Req, Resp proto.Message](newReq func() Req, call func(context.Context, Req, ...grpc.CallOption) (Resp, error)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, 1<<16))
		req := newReq()
		if err == nil {
			err = protojson.Unmarshal(body, req)
		}
		if err != nil {
			http.Error(w, http.StatusText(http.StatusBadRequest), http.StatusBadRequest)
			return
		}

		ctx, cancel := context.WithTimeout(r.Context(), authTimeout)
		defer cancel()
		resp, err := call(ctx, req)
		if err != nil {
			code := httpStatus(err)
			http.Error(w, http.StatusText(code), code)
			return
		}

		out, err := jsonOut.Marshal(resp)
		if err != nil {
			http.Error(w, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write(out)
	}
}

func httpStatus(err error) int {
	switch status.Code(err) {
	case codes.InvalidArgument:
		return http.StatusBadRequest
	case codes.Unauthenticated:
		return http.StatusUnauthorized
	case codes.Unavailable:
		return http.StatusServiceUnavailable
	case codes.DeadlineExceeded:
		return http.StatusGatewayTimeout
	default:
		return http.StatusBadGateway
	}
}
