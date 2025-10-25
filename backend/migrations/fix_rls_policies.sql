-- Fix RLS policies for users table
-- Run this in Supabase SQL Editor

-- Drop existing policies that might be causing issues
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Service role can manage users" ON users;
DROP POLICY IF EXISTS "Users can insert their own profile" ON users;

-- Create proper RLS policies for users table

-- Policy for inserting users (allow authenticated users to create their own record)
CREATE POLICY "Users can insert their own profile" ON users
  FOR INSERT TO authenticated WITH CHECK (
    google_id = auth.uid()::text
  );

-- Policy for viewing users (allow users to view their own profile)
CREATE POLICY "Users can view own profile" ON users
  FOR SELECT TO authenticated USING (
    google_id = auth.uid()::text
  );

-- Policy for updating users (allow users to update their own profile)
CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE TO authenticated USING (
    google_id = auth.uid()::text
  );

-- Service role can do everything
CREATE POLICY "Service role full access to users" ON users
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Also fix documents table policies to ensure they work properly
DROP POLICY IF EXISTS "Users can read own and global documents" ON documents;
DROP POLICY IF EXISTS "Users can read documents based on course" ON documents;
DROP POLICY IF EXISTS "Service role can manage documents" ON documents;

-- Documents policies
CREATE POLICY "Users can view own documents" ON documents
  FOR SELECT TO authenticated USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can insert own documents" ON documents
  FOR INSERT TO authenticated WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can update own documents" ON documents
  FOR UPDATE TO authenticated USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can delete own documents" ON documents
  FOR DELETE TO authenticated USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- Service role full access to documents
CREATE POLICY "Service role full access to documents" ON documents
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Enable RLS on both tables if not already enabled
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create a function to get user ID from Google ID that works with RLS
CREATE OR REPLACE FUNCTION get_user_id_from_google_id(google_id_param text)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_id_val bigint;
BEGIN
  SELECT id INTO user_id_val
  FROM users
  WHERE google_id = google_id_param;

  RETURN user_id_val;
END;
$$;