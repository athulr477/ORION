describe('Authentication', () => {
  it('should authenticate a valid user', async () => {
    // Verify that a user can authenticate with valid credentials.
    const response = await client.post('/auth/login', { user: 'admin', pass: 'secret' });
    expect(response.status).toBe(200);
    expect(response.data.token).toBeDefined();
    assert.strictEqual(response.data.error, undefined);
  });
});
