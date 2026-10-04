package main

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"time"

	"github.com/valkey-io/valkey-go"
)

const sessionTTL = 30 * 24 * time.Hour

var (
	errSessionNotFound = errors.New("session not found")
	errTokenReused     = errors.New("refresh token reused")
)

type session struct {
	AccountID string `json:"account_id"`
	Epoch     int64  `json:"epoch"`
	Hash      string `json:"hash"`
}

func sessionKey(familyID string) string {
	return "session:" + familyID
}

func hashSecret(secret string) string {
	sum := sha256.Sum256([]byte(secret))
	return b64(sum[:])
}

func (s *authServer) createSession(ctx context.Context, familyID string, sess session) error {
	value, err := json.Marshal(sess)
	if err != nil {
		return err
	}
	return s.store.Do(ctx, s.store.B().Set().Key(sessionKey(familyID)).Value(string(value)).Ex(sessionTTL).Build()).Error()
}

func getSession(ctx context.Context, c valkey.CoreClient, familyID string) (session, error) {
	var sess session
	raw, err := c.Do(ctx, c.B().Get().Key(sessionKey(familyID)).Build()).AsBytes()
	if valkey.IsValkeyNil(err) {
		return sess, errSessionNotFound
	}
	if err != nil {
		return sess, err
	}
	return sess, json.Unmarshal(raw, &sess)
}

// WATCH makes EXEC abort if a concurrent refresh rotated the session first.
func (s *authServer) rotateSession(ctx context.Context, familyID, oldHash, newHash string) error {
	key := sessionKey(familyID)
	return s.store.Dedicated(func(c valkey.DedicatedClient) error {
		if err := c.Do(ctx, c.B().Watch().Key(key).Build()).Error(); err != nil {
			return err
		}
		sess, err := getSession(ctx, c, familyID)
		if err == nil && sess.Hash != oldHash {
			err = errTokenReused
		}
		if err != nil {
			c.Do(ctx, c.B().Unwatch().Build())
			return err
		}

		sess.Hash = newHash
		value, err := json.Marshal(sess)
		if err != nil {
			c.Do(ctx, c.B().Unwatch().Build())
			return err
		}
		res := c.DoMulti(ctx,
			c.B().Multi().Build(),
			c.B().Set().Key(key).Value(string(value)).Keepttl().Build(),
			c.B().Exec().Build(),
		)
		err = res[len(res)-1].Error()
		if valkey.IsValkeyNil(err) {
			return errTokenReused
		}
		return err
	})
}

func (s *authServer) deleteSession(ctx context.Context, familyID string) error {
	return s.store.Do(ctx, s.store.B().Del().Key(sessionKey(familyID)).Build()).Error()
}
