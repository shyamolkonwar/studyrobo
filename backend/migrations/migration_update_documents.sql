-- Migration to update documents table for multi-tenant RAG system
-- Add user_id and file name columns

-- Add user_id column to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id bigint REFERENCES users(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_file_name text;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_type text; -- 'pdf', 'docx', 'global'
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path text; -- Supabase Storage path

-- Add index for user_id for better performance
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

-- Update documents policies for user-specific access
DROP POLICY IF EXISTS "Authenticated users can read documents" ON documents;
DROP POLICY IF EXISTS "Service role can manage documents" ON documents;

-- New policies for user-specific document access
CREATE POLICY "Users can read own and global documents" ON documents
  FOR SELECT TO authenticated USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    ) OR user_id IS NULL -- Global documents
  );

CREATE POLICY "Users can read documents based on course" ON documents
  FOR SELECT TO authenticated USING (
    -- Allow access to documents that match user's course
    user_id IS NULL AND course_name IN (
      SELECT course_name FROM users WHERE google_id = auth.uid()::text
    )
  );

CREATE POLICY "Service role can manage documents" ON documents
  FOR ALL TO service_role USING (true);

-- Update match_documents function to filter by user and include both user-specific and course-related documents
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  user_course text DEFAULT NULL -- Optional course filter
)
returns table (
  id bigint,
  content text,
  similarity float,
  file_name text,
  file_type text,
  is_global boolean
)
language plpgsql
security definer
as $$
declare
  current_user_id bigint;
  user_course_name text;
begin
  -- Check if user is authenticated
  if auth.uid() is null then
    raise exception 'Authentication required';
  end if;

  -- Get current user's ID and course
  select id, course_name into current_user_id, user_course_name
  from users
  where google_id = auth.uid()::text;

  if current_user_id is null then
    raise exception 'User not found';
  end if;

  -- Use provided course or user's course
  user_course_name := COALESCE(user_course, user_course_name);

  return query
  select
    documents.id,
    documents.content,
    1 - (documents.embedding <=> query_embedding) as similarity,
    documents.original_file_name as file_name,
    documents.file_type,
    (documents.user_id IS NULL) as is_global
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
    AND (
      -- User's own documents
      documents.user_id = current_user_id
      OR
      -- Global documents matching user's course
      (documents.user_id IS NULL AND documents.course_name = user_course_name)
      OR
      -- Public/global documents without course restriction
      (documents.user_id IS NULL AND documents.course_name IS NULL)
    )
  order by similarity desc
  limit match_count;
end;
$$;

-- Create a simplified version for backward compatibility
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
  user_course_name text;
begin
  -- Check if user is authenticated
  if auth.uid() is null then
    raise exception 'Authentication required';
  end if;

  -- Get current user's ID and course
  select id, course_name into current_user_id, user_course_name
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
      -- Global documents matching user's course
      (documents.user_id IS NULL AND documents.course_name = user_course_name)
      OR
      -- Public/global documents without course restriction
      (documents.user_id IS NULL AND documents.course_name IS NULL)
    )
  order by similarity desc
  limit match_count;
end;
$$;