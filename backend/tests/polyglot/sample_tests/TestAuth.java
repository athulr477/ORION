import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AuthenticationTest {
    
    /**
     * Verify that a user can authenticate with valid credentials.
     */
    @Test
    void testUserAuthentication() {
        Response response = client.post("/auth/login", new LoginRequest("admin", "secret"));
        assertEquals(200, response.getStatusCode());
        assertNotNull(response.getBody().getToken());
    }
}
