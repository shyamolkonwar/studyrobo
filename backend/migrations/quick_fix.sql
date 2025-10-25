-- Quick fix for the database issues
-- Run this in Supabase SQL Editor

-- First, ensure users table has all required columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id text UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS name text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS course_name text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS major text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS university text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS semester text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed boolean DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed_at timestamptz;

-- Ensure documents table has all required columns
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id bigint REFERENCES users(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_file_name text;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_type text;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path text;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status text DEFAULT 'completed';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS course_name text;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);

-- Drop the problematic overloaded functions
DROP FUNCTION IF EXISTS match_documents(query_embedding vector, match_threshold float, match_count int);
DROP FUNCTION IF EXISTS match_documents(query_embedding vector, match_threshold float, match_count int, user_course text);

-- Create a simple working function
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id bigint,
  content text,
  similarity float
)
language plpgsql
security definer
as $$
declare
  current_user_id bigint;
begin
  -- Check if user is authenticated
  if auth.uid() is null then
    raise exception 'Authentication required';
  end if;

  -- Get current user's ID
  select id into current_user_id
  from users
  where google_id = auth.uid()::text;

  if current_user_id is null then
    raise exception 'User not found';
  end if;

  return query
  select
    documents.id,
    documents.content,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
    AND (
      -- User's own documents
      documents.user_id = current_user_id
      OR
      -- Global documents
      documents.user_id IS NULL
    )
  order by similarity desc
  limit match_count;
end;
$$;

-- Update RLS policies for users table
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Service role can manage users" ON users;

CREATE POLICY "Users can view own profile" ON users
  FOR SELECT TO authenticated USING (google_id = auth.uid()::text);

CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE TO authenticated USING (google_id = auth.uid()::text);

CREATE POLICY "Service role can manage users" ON users
  FOR ALL TO service_role USING (true);

-- Enable RLS on users table if not already enabled
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Enable RLS on documents table if not already enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;