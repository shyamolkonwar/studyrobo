-- Complete reset of RLS policies for documents table
-- Run this in Supabase SQL Editor to fix all document upload issues

-- Drop ALL existing policies on documents table
DROP POLICY IF EXISTS "Authenticated users can read documents" ON documents;
DROP POLICY IF EXISTS "Service role can manage documents" ON documents;
DROP POLICY IF EXISTS "Service role full access to documents" ON documents;
DROP POLICY IF EXISTS "Users can read own and global documents" ON documents;
DROP POLICY IF EXISTS "Users can read documents based on course" ON documents;
DROP POLICY IF EXISTS "Users can view own documents" ON documents;
DROP POLICY IF EXISTS "Users can insert own documents" ON documents;
DROP POLICY IF EXISTS "Users can update own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON documents;
DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

-- Create clean, working RLS policies

-- 1. Allow all authenticated users to read all documents (temporary fix)
CREATE POLICY "Authenticated users can read documents" ON documents
  FOR SELECT TO authenticated
  USING (true);

-- 2. Allow authenticated users to insert documents for themselves
CREATE POLICY "Users can insert documents" ON documents
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- 3. Allow users to update their own documents
CREATE POLICY "Users can update own documents" ON documents
  FOR UPDATE TO authenticated
  USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  )
  WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- 4. Allow users to delete their own documents
CREATE POLICY "Users can delete own documents" ON documents
  FOR DELETE TO authenticated
  USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- 5. Service role has full access (for backend operations)
CREATE POLICY "Service role full access" ON documents
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

-- Ensure RLS is enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
