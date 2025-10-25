-- Supabase Database Setup Script for StudyRobo Pivot
-- Run this in Supabase SQL Editor

-- 1. Enable the vector extension
create extension vector;

-- 2. Create table for RAG documents (replaces ChromaDB)
create table documents (
  id bigserial primary key,
  content text,
  course_name text,
  -- Match your embedding model, e.g., 1536 for OpenAI
  embedding vector(1536)
);

-- 3. Create RPC function for document search
-- This function is a "Remote Procedure Call" (RPC)
-- It lets you search for vectors from your Python backend
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

-- 4. Create table for chat history (memory)
create table messages (
  id bigserial primary key,
  -- Links this message to a specific user in Supabase Auth
  user_id uuid references auth.users(id),
  role text, -- 'user' or 'ai'
  content text,
  created_at timestamptz default now()
);

-- 5. Create table for attendance tracking
create table attendance (
  id bigserial primary key,
  user_id uuid references auth.users(id),
  course_name text,
  marked_at timestamptz default now()
);

-- 6. Create indexes for better performance
create index on documents using ivfflat (embedding vector_cosine_ops);
create index on messages (user_id, created_at);
create index on attendance (user_id, course_name);

-- 7. Enable Row Level Security (RLS) for security
alter table messages enable row level security;
alter table attendance enable row level security;

-- 8. Create RLS policies
-- Users can only see their own messages
create policy "Users can view own messages" on messages
  for select using (auth.uid() = user_id);

create policy "Users can insert own messages" on messages
  for insert with check (auth.uid() = user_id);

-- Users can only see their own attendance records
create policy "Users can view own attendance" on attendance
  for select using (auth.uid() = user_id);

create policy "Users can insert own attendance" on attendance
  for insert with check (auth.uid() = user_id);