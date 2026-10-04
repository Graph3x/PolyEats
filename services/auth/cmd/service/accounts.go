package main

import (
	"context"
	"errors"
)

var (
	errInvalidCredentials = errors.New("invalid credentials")
	errAccountNotFound    = errors.New("account not found")
)

type accountIdentity struct {
	AccountID string `json:"account_id"`
	Role      string `json:"role"`
	Epoch     int64  `json:"epoch"`
}

type accountState struct {
	Role  string `json:"role"`
	Epoch int64  `json:"epoch"`
}

// TODO: replace with HTTP calls to account (s.account, s.accountURL) once it exists.
var hardcodedAccounts = []struct {
	email    string
	password string
	identity accountIdentity
}{
	{"customer@polyeats.test", "customer", accountIdentity{"acc-customer", "customer", 1}},
	{"restaurant@polyeats.test", "restaurant", accountIdentity{"acc-restaurant", "restaurant", 1}},
	{"courier@polyeats.test", "courier", accountIdentity{"acc-courier", "courier", 1}},
}

func (s *authServer) verifyCredentials(ctx context.Context, email, password string) (accountIdentity, error) {
	for _, a := range hardcodedAccounts {
		if a.email == email && a.password == password {
			return a.identity, nil
		}
	}
	return accountIdentity{}, errInvalidCredentials
}

func (s *authServer) getAccountState(ctx context.Context, accountID string) (accountState, error) {
	for _, a := range hardcodedAccounts {
		if a.identity.AccountID == accountID {
			return accountState{Role: a.identity.Role, Epoch: a.identity.Epoch}, nil
		}
	}
	return accountState{}, errAccountNotFound
}
