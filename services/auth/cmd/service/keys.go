package main

import (
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"math/big"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

const (
	issuer         = "auth"
	accessTokenTTL = 5 * time.Minute
)

type signingKey struct {
	kid string
	key *rsa.PrivateKey
}

type keySet struct {
	keys   []signingKey
	active int
}

type accessClaims struct {
	Role string `json:"role"`
	jwt.RegisteredClaims
}

type jwk struct {
	Kty string `json:"kty"`
	Kid string `json:"kid"`
	Use string `json:"use"`
	Alg string `json:"alg"`
	N   string `json:"n"`
	E   string `json:"e"`
}

func loadKeySet(path string) (*keySet, error) {
	pemBytes, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	key, err := jwt.ParseRSAPrivateKeyFromPEM(pemBytes)
	if err != nil {
		return nil, err
	}
	return &keySet{keys: []signingKey{{kid: thumbprint(&key.PublicKey), key: key}}}, nil
}

func (ks *keySet) issueAccessToken(accountID, role string) (string, error) {
	now := time.Now()
	claims := accessClaims{
		Role:      role,
		Subject:   accountID,
		Issuer:    issuer,
		IssuedAt:  jwt.NewNumericDate(now),
		ExpiresAt: jwt.NewNumericDate(now.Add(accessTokenTTL)),
	}
	active := ks.keys[ks.active]
	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	token.Header["kid"] = active.kid
	return token.SignedString(active.key)
}

func (ks *keySet) jwks() ([]byte, error) {
	keys := make([]jwk, len(ks.keys))
	for i, k := range ks.keys {
		pub := &k.key.PublicKey
		keys[i] = jwk{Kty: "RSA", Kid: k.kid, Use: "sig", Alg: "RS256", N: b64(pub.N.Bytes()), E: b64(big.NewInt(int64(pub.E)).Bytes())}
	}
	return json.Marshal(map[string][]jwk{"keys": keys})
}

// RFC 7638: members in lexicographic order, no whitespace.
func thumbprint(pub *rsa.PublicKey) string {
	canonical := `{"e":"` + b64(big.NewInt(int64(pub.E)).Bytes()) + `","kty":"RSA","n":"` + b64(pub.N.Bytes()) + `"}`
	sum := sha256.Sum256([]byte(canonical))
	return b64(sum[:])
}

func b64(b []byte) string {
	return base64.RawURLEncoding.EncodeToString(b)
}
