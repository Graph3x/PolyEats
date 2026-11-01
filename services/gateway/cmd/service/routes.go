package main

import (
	"errors"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

var routes = map[string]string{
	"order-tracking":  "http://order-tracking:8080",
	"user":            "http://user:8080",
	"address":         "http://address:8080",
	"restaurant":      "http://restaurant:8080",
	"account":         "http://account:8080",
	"courier-profile": "http://courier-profile:8080",
	"review":          "http://review:8080",
}

var publicRoutes = map[string][]string{
	"account": {"POST /account/accounts"},
}

func registerRoutes(mux *http.ServeMux, auth *verifier) error {
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.DialContext = (&net.Dialer{Timeout: 2 * time.Second}).DialContext
	transport.ResponseHeaderTimeout = 5 * time.Second
	upstream := otelhttp.NewTransport(transport)

	for prefix, base := range routes {
		target, err := url.Parse(base)
		if err != nil {
			return err
		}
		proxy := &httputil.ReverseProxy{
			Rewrite:      func(r *httputil.ProxyRequest) { r.SetURL(target) },
			Transport:    upstream,
			ErrorHandler: proxyError,
		}
		handler := http.StripPrefix("/"+prefix, proxy)
		mux.Handle("/"+prefix+"/", auth.middleware(handler))
		for _, pattern := range publicRoutes[prefix] {
			mux.Handle(pattern, handler)
		}
	}
	return nil
}

func proxyError(w http.ResponseWriter, r *http.Request, err error) {
	code := http.StatusBadGateway
	var netErr net.Error
	if errors.As(err, &netErr) && netErr.Timeout() {
		code = http.StatusGatewayTimeout
	}
	log.Printf("proxy %s: %v", r.URL.Path, err)
	http.Error(w, http.StatusText(code), code)
}
