-- Create user_connections table for storage of OAuth tokens
-- Simplified version for demo/hackathon - in production use pgsodium encryption

-- 1. Create the table to store the connections
create table user_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  app_name text not null, -- e.g., "gmail"

  -- Store the refresh token (in production, encrypt this with pgsodium)
  refresh_token text not null,

  -- Store additional token metadata
  access_token text,
  expires_at timestamp with time zone,

  -- Ensure a user can only connect each app once
  unique(user_id, app_name),

  -- Add timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. Create an index for faster lookups
create index idx_user_connections_user_id on user_connections(user_id);
create index idx_user_connections_app_name on user_connections(app_name);

-- 4. Enable Row Level Security (RLS)
alter table user_connections enable row level security;

-- 5. Create RLS policies so users can only access their own connections
create policy "Users can view their own connections"
  on user_connections for select
  using (auth.uid() = user_id);

create policy "Users can insert their own connections"
  on user_connections for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own connections"
  on user_connections for update
  using (auth.uid() = user_id);

create policy "Users can delete their own connections"
  on user_connections for delete
  using (auth.uid() = user_id);

-- 6. Create a function to automatically update the updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = timezone('utc'::text, now());
    return new;
end;
$$ language 'plpgsql';

-- 7. Create the trigger
create trigger update_user_connections_updated_at
    before update on user_connections
    for each row
    execute procedure update_updated_at_column();
