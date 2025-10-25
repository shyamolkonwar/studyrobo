-- Migration to update users table for personalized RAG system
-- Add course information and onboarding fields

-- Add course-related columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS course_name text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS major text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS university text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS semester text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed boolean DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed_at timestamptz;

-- Update get_or_create_user function to handle new fields
CREATE OR REPLACE FUNCTION get_or_create_user(
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

  -- If not found, create new user (onboarding not completed yet)
  if user_id is null then
    insert into users (google_id, email, name, onboarding_completed)
    values (p_google_id, p_email, p_name, false)
    returning id into user_id;
  end if;

  return user_id;
end;
$$;

-- Create function to check if user has completed onboarding
CREATE OR REPLACE FUNCTION has_completed_onboarding(p_google_id text)
returns boolean
language plpgsql
security definer
as $$
declare
  completed boolean;
begin
  select onboarding_completed into completed
  from users
  where google_id = p_google_id;

  return COALESCE(completed, false);
end;
$$;

-- Create function to update user onboarding information
CREATE OR REPLACE FUNCTION complete_user_onboarding(
  p_google_id text,
  p_course_name text,
  p_major text,
  p_university text,
  p_semester text
)
returns void
language plpgsql
security definer
as $$
begin
  update users
  set
    course_name = p_course_name,
    major = p_major,
    university = p_university,
    semester = p_semester,
    onboarding_completed = true,
    onboarding_completed_at = now()
  where google_id = p_google_id;
end;
$$;