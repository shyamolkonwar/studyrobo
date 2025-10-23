try:
    from supabase import create_client, Client
except ImportError:
    # Fallback for dependency issues
    def create_client(url: str, key: str):
        # Mock client for when supabase package has issues
        class MockClient:
            def auth(self):
                return MockAuth()
        class MockAuth:
            def get_user(self, token):
                # Mock implementation
                return {"user": {"id": "mock_user", "email": "mock@example.com"}}
        return MockClient()

    class Client:
        pass
from .config import settings

# Create Supabase client with service role key for backend operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

# Create Supabase client with anon key for user-facing operations (if needed)
supabase_anon: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
