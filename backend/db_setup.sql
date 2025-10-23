-- Database Setup Script for StudyRobo
-- Run this in Supabase SQL Editor or via psql

-- 1. Enable the vector extension
create extension if not exists vector;

-- 2. Create table for users
create table users (
  id bigserial primary key,
  google_id text unique,
  email text,
  name text,
  created_at timestamptz default now()
);

-- 3. Create table for RAG documents
create table documents (
  id bigserial primary key,
  content text,
  course_name text,
  -- Match your embedding model, e.g., 1536 for OpenAI
  embedding vector(1536)
);

-- 4. Create RPC function for document search
create or replace function match_documents (
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
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
end;
$$;

-- 5. Create table for chat history (memory)
create table messages (
  id bigserial primary key,
  user_id bigint references users(id),
  role text, -- 'user' or 'ai'
  content text,
  created_at timestamptz default now()
);

-- 6. Create table for attendance tracking
create table attendance (
  id bigserial primary key,
  user_id bigint references users(id),
  course_name text,
  marked_at timestamptz default now()
);

-- 7. Create indexes for better performance
create index on documents using ivfflat (embedding vector_cosine_ops);
create index on messages (user_id, created_at);
create index on attendance (user_id, course_name);
