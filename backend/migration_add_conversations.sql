-- Migration Script for StudyRobo Chat Enhancement
-- Run this in Supabase SQL Editor to add conversation support

-- 1. Create conversations table
create table conversations (
  id uuid primary key default gen_random_uuid(),
  user_id bigint references users(id),
  title text,
  created_at timestamptz default now()
);

-- 2. Add conversation_id to messages table
alter table messages
add column conversation_id uuid references conversations(id);

-- 3. Create indexes for better performance
create index on conversations (user_id, created_at);
create index on messages (conversation_id, created_at);

-- 4. Enable RLS on conversations table
alter table conversations enable row level security;

-- Users can only see their own conversations
create policy "Users can view own conversations" on conversations
  for select using (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

create policy "Users can create own conversations" on conversations
  for insert with check (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

-- Users can update their own conversations (for title changes)
create policy "Users can update own conversations" on conversations
  for update using (
    user_id in (
      select id from users where google_id = auth.uid()::text
    )
  );

-- Service role can manage all conversations
create policy "Service role can manage conversations" on conversations
  for all to service_role using (true);

-- 5. Update messages policies to include conversation_id check
-- Drop existing policies first
drop policy if exists "Users can view own messages" on messages;
drop policy if exists "Users can insert own messages" on messages;
drop policy if exists "Service role can manage messages" on messages;

-- Recreate policies with conversation checks
create policy "Users can view own messages" on messages
  for select using (
    conversation_id in (
      select id from conversations
      where user_id in (
        select id from users where google_id = auth.uid()::text
      )
    )
  );

create policy "Users can insert own messages" on messages
  for insert with check (
    conversation_id in (
      select id from conversations
      where user_id in (
        select id from users where google_id = auth.uid()::text
      )
    )
  );

-- Service role can manage all messages
create policy "Service role can manage messages" on messages
  for all to service_role using (true);

-- 6. Create function to get or create conversation
create or replace function get_or_create_conversation(
  p_user_id bigint,
  p_title text default null
)
returns uuid
language plpgsql
security definer
as $$
declare
  conversation_id uuid;
begin
  -- If no title provided, create new conversation
  if p_title is null then
    insert into conversations (user_id, title)
    values (p_user_id, 'New Chat')
    returning id into conversation_id;
  else
    -- Create conversation with provided title
    insert into conversations (user_id, title)
    values (p_user_id, p_title)
    returning id into conversation_id;
  end if;

  return conversation_id;
end;
$$;

-- 7. Function to create conversation from user_id (for backend use)
create or replace function create_conversation_for_user(
  p_google_id text,
  p_title text default 'New Chat'
)
returns uuid
language plpgsql
security definer
as $$
declare
  user_id bigint;
  conversation_id uuid;
begin
  -- Get user ID from Google ID
  select id into user_id from users where google_id = p_google_id;

  if user_id is null then
    raise exception 'User not found for Google ID: %', p_google_id;
  end if;

  -- Create conversation
  insert into conversations (user_id, title)
  values (user_id, p_title)
  returning id into conversation_id;

  return conversation_id;
end;
$$;

-- 8. Update message insert function to include conversation_id
create or replace function add_message_to_conversation(
  p_conversation_id uuid,
  p_role text,
  p_content text
)
returns bigint
language plpgsql
security definer
as $$
declare
  message_id bigint;
begin
  -- Verify conversation exists and user has access
  if not exists (
    select 1 from conversations
    where id = p_conversation_id
    and user_id in (
      select id from users where google_id = auth.uid()::text
    )
  ) then
    raise exception 'Conversation not found or access denied';
  end if;

  -- Insert message
  insert into messages (conversation_id, role, content, user_id)
  select p_conversation_id, p_role, p_content, user_id
  from conversations
  where id = p_conversation_id
  returning id into message_id;

  return message_id;
end;
$$;
