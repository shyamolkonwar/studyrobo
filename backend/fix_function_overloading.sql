-- Fix function overloading issue by renaming the functions
-- Run this in Supabase SQL Editor

-- Drop the overloaded functions
DROP FUNCTION IF EXISTS match_documents(query_embedding vector, match_threshold float, match_count int);
DROP FUNCTION IF EXISTS match_documents(query_embedding vector, match_threshold float, match_count int, user_course text);

-- Create a single function with optional parameter
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

-- Create a simplified version for backward compatibility (different name)
CREATE OR REPLACE FUNCTION match_documents_simple (
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