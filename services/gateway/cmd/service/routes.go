package main

import (
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

var routes = map[string]string{
	"order-tracking": "http://order-tracking:8080",
}

func registerRoutes(mux *http.ServeMux) error {
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
			Rewrite:   func(r *httputil.ProxyRequest) { r.SetURL(target) },
			Transport: upstream,
		}
		mux.Handle("/"+prefix+"/", http.StripPrefix("/"+prefix, proxy))
	}
	return nil
}
