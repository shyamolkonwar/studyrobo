from supabase import create_client, Client
from .config import settings

# Create Supabase client with service role key for backend operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

# Create Supabase client with anon key for user-facing operations (if needed)
supabase_anon: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
