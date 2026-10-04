package main

import (
	"context"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

const (
	jwtIssuer       = "auth"
	jwksCacheTTL    = time.Hour
	jwksRefetchWait = 10 * time.Second
)

var (
	errMissingToken    = errors.New("missing bearer token")
	errUnknownKid      = errors.New("unknown kid")
	errJWKSUnavailable = errors.New("jwks unavailable")
)

type claims struct {
	Role string `json:"role"`
	jwt.RegisteredClaims
}

type verifier struct {
	jwksURL string
	client  *http.Client

	mu          sync.Mutex
	keys        map[string]*rsa.PublicKey
	fetchedAt   time.Time
	attemptedAt time.Time
	fetchErr    error
}

func newVerifier(jwksURL string) *verifier {
	return &verifier{
		jwksURL: jwksURL,
		client: &http.Client{
			Timeout:   5 * time.Second,
			Transport: otelhttp.NewTransport(http.DefaultTransport),
		},
	}
}

func (v *verifier) middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, err := v.verify(r.Context(), r.Header.Get("Authorization"))
		if errors.Is(err, errJWKSUnavailable) {
			http.Error(w, http.StatusText(http.StatusServiceUnavailable), http.StatusServiceUnavailable)
			return
		}
		if err != nil {
			w.Header().Set("WWW-Authenticate", "Bearer")
			http.Error(w, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (v *verifier) verify(ctx context.Context, authorization string) (*claims, error) {
	raw, ok := strings.CutPrefix(authorization, "Bearer ")
	if !ok {
		return nil, errMissingToken
	}
	c := &claims{}
	_, err := jwt.ParseWithClaims(raw, c, func(t *jwt.Token) (any, error) {
		kid, _ := t.Header["kid"].(string)
		return v.key(ctx, kid)
	}, jwt.WithValidMethods([]string{"RS256"}), jwt.WithIssuer(jwtIssuer), jwt.WithExpirationRequired())
	return c, err
}

// A stale key is still served when a refetch fails, so an auth outage does not reject valid tokens.
func (v *verifier) key(ctx context.Context, kid string) (*rsa.PublicKey, error) {
	v.mu.Lock()
	defer v.mu.Unlock()

	key, known := v.keys[kid]
	if known && time.Since(v.fetchedAt) < jwksCacheTTL {
		return key, nil
	}
	if time.Since(v.attemptedAt) >= jwksRefetchWait {
		v.attemptedAt = time.Now()
		keys, err := v.fetch(ctx)
		v.fetchErr = err
		if err == nil {
			v.keys, v.fetchedAt = keys, time.Now()
			key, known = keys[kid]
		}
	}
	if known {
		return key, nil
	}
	if v.fetchErr != nil {
		return nil, fmt.Errorf("%w: %v", errJWKSUnavailable, v.fetchErr)
	}
	return nil, errUnknownKid
}

func (v *verifier) fetch(ctx context.Context) (map[string]*rsa.PublicKey, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, v.jwksURL, nil)
	if err != nil {
		return nil, err
	}
	resp, err := v.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("jwks status %d", resp.StatusCode)
	}

	var set struct {
		Keys []struct {
			Kty string `json:"kty"`
			Kid string `json:"kid"`
			N   string `json:"n"`
			E   string `json:"e"`
		} `json:"keys"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&set); err != nil {
		return nil, err
	}

	keys := make(map[string]*rsa.PublicKey, len(set.Keys))
	for _, k := range set.Keys {
		if k.Kty != "RSA" {
			continue
		}
		n, errN := base64.RawURLEncoding.DecodeString(k.N)
		e, errE := base64.RawURLEncoding.DecodeString(k.E)
		if errN != nil || errE != nil {
			continue
		}
		keys[k.Kid] = &rsa.PublicKey{N: new(big.Int).SetBytes(n), E: int(new(big.Int).SetBytes(e).Int64())}
	}
	return keys, nil
}
