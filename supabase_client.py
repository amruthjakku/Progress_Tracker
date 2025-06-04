from supabase import create_client, Client

SUPABASE_URL = "https://sfadhqdgqxcfniyousde.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNmYWRocWRncXhjZm5peW91c2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkwMzk5NzEsImV4cCI6MjA2NDYxNTk3MX0.kMvlGx_zAjZ6mBT1qe_py90Fw7aqfxajpWZLQkS1LDA"


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY) 