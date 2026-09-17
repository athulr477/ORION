def test_user_authentication():
    """Verify that a user can authenticate with valid credentials."""
    response = client.post("/auth/login", json={"user": "admin", "pass": "secret"})
    assert response.status_code == 200
    assert response.json()["token"] is not None
    assert "error" not in response.json()
