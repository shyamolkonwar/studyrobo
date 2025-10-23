-- Database Setup Script for StudyRobo
-- Run this in Supabase SQL Editor

-- 1. Enable the vector extension
create extension if not exists vector;

-- 2. Enable Row Level Security globally
-- Note: RLS is enabled per table

-- 3. Create table for users
create table users (
  id bigserial primary key,
  google_id text unique,
  email text,
  name text,
  created_at timestamptz default now()
);

-- Enable RLS on users table
alter table users enable row level security;

-- Users can only see their own data
create policy "Users can view own data" on users
  for select using (auth.uid()::text = google_id);

create policy "Users can update own data" on users
  for update using (auth.uid()::text = google_id);

-- 4. Create table for RAG documents
create table documents (
  id bigserial primary key,
  content text,
  course_name text,
  -- Match your embedding model, e.g., 1536 for OpenAI
  embedding vector(1536)
);

-- Documents are readable by all authenticated users (shared knowledge base)
alter table documents enable row level security;

create policy "Authenticated users can read documents" on documents
  for select to authenticated using (true);

-- Only service role can insert/update documents (for ingestion)
create policy "Service role can manage documents" on documents
  for all to service_role using (true);

-- 5. Create RPC function for document search
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
security definer
as $$
begin
  -- Check if user is authenticated
  if auth.uid() is null then
    raise exception 'Authentication required';
  end if;

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

-- 6. Create table for chat history (memory)
create table messages (
  id bigserial primary key,
  user_id bigint references users(id),
  role text, -- 'user' or 'ai'
  content text,
  created_at timestamptz default now()
);

-- Enable RLS on messages table
alter table messages enable row level security;

-- Users can only see their own messages
create policy "Users can view own messages" on messages
  for select using (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

create policy "Users can insert own messages" on messages
  for insert with check (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

-- Service role can manage all messages
create policy "Service role can manage messages" on messages
  for all to service_role using (true);

-- 7. Create table for attendance tracking
create table attendance (
  id bigserial primary key,
  user_id bigint references users(id),
  course_name text,
  marked_at timestamptz default now()
);

-- Enable RLS on attendance table
alter table attendance enable row level security;

-- Users can only see their own attendance records
create policy "Users can view own attendance" on attendance
  for select using (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

create policy "Users can insert own attendance" on attendance
  for insert with check (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

-- Service role can manage all attendance
create policy "Service role can manage attendance" on attendance
  for all to service_role using (true);

-- 8. Create indexes for better performance
create index on documents using ivfflat (embedding vector_cosine_ops);
create index on messages (user_id, created_at);
create index on attendance (user_id, course_name);

-- 9. Create a function to get or create user from Google ID
create or replace function get_or_create_user(
  p_google_id text,
  p_email text,
  p_name text
)
returns bigint
language plpgsql
security definer
as $$
declare
  user_id bigint;
begin
  -- Try to find existing user
  select id into user_id from users where google_id = p_google_id;

  -- If not found, create new user
  if user_id is null then
    insert into users (google_id, email, name)
    values (p_google_id, p_email, p_name)
    returning id into user_id;
  end if;

  return user_id;
end;
$$;
