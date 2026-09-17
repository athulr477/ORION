package auth_test

import (
	"testing"
	"net/http"
	"github.com/stretchr/testify/assert"
)

// TestUserAuthentication verifies that a user can authenticate with valid credentials.
func TestUserAuthentication(t *testing.T) {
	response := client.Post("/auth/login", map[string]string{"user": "admin", "pass": "secret"})
	assert.Equal(t, http.StatusOK, response.StatusCode)
	assert.NotNil(t, response.Token)
}
