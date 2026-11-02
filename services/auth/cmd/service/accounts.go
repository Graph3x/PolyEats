package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

var (
	errInvalidCredentials = errors.New("invalid credentials")
	errAccountNotFound    = errors.New("account not found")
)

type accountIdentity struct {
	AccountID string `json:"accountId"`
	Role      string `json:"role"`
	Epoch     int64  `json:"epoch"`
}

type accountState struct {
	Role  string `json:"role"`
	Epoch int64  `json:"epoch"`
}

func (s *authServer) verifyCredentials(ctx context.Context, email, password string) (accountIdentity, error) {
	var identity accountIdentity
	code, err := s.callAccount(ctx, http.MethodPost, "/accounts/verify", map[string]string{"email": email, "password": password}, &identity)
	switch {
	case err != nil:
		return identity, err
	case code == http.StatusUnauthorized:
		return identity, errInvalidCredentials
	case code != http.StatusOK:
		return identity, fmt.Errorf("account verify: status %d", code)
	}
	return identity, nil
}

func (s *authServer) getAccountState(ctx context.Context, accountID string) (accountState, error) {
	var state accountState
	code, err := s.callAccount(ctx, http.MethodGet, "/accounts/"+url.PathEscape(accountID)+"/state", nil, &state)
	switch {
	case err != nil:
		return state, err
	case code == http.StatusNotFound:
		return state, errAccountNotFound
	case code != http.StatusOK:
		return state, fmt.Errorf("account state: status %d", code)
	}
	return state, nil
}

func (s *authServer) callAccount(ctx context.Context, method, path string, body, out any) (int, error) {
	var reader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return 0, err
		}
		reader = bytes.NewReader(b)
	}
	req, err := http.NewRequestWithContext(ctx, method, s.accountURL+path, reader)
	if err != nil {
		return 0, err
	}
	token, err := s.keys.issueAccessToken("auth", "service")
	if err != nil {
		return 0, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.account.Do(req)
	if err != nil {
		return 0, err
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode != http.StatusOK {
		return resp.StatusCode, nil
	}
	return resp.StatusCode, json.NewDecoder(resp.Body).Decode(out)
}
