-- Fix RLS policies for documents table to allow authenticated users to insert their own documents
-- Run this in Supabase SQL Editor

-- Drop existing policies that might conflict
DROP POLICY IF EXISTS "Authenticated users can read documents" ON documents;
DROP POLICY IF EXISTS "Service role can manage documents" ON documents;
DROP POLICY IF EXISTS "Service role full access to documents" ON documents;

-- Create proper RLS policies for documents table

-- Policy for reading documents (authenticated users can read all documents - shared knowledge base)
CREATE POLICY "Authenticated users can read documents" ON documents
  FOR SELECT TO authenticated
  USING (true);

-- Policy for inserting documents (authenticated users can insert their own documents)
CREATE POLICY "Users can insert their own documents" ON documents
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- Policy for updating documents (authenticated users can update their own documents)
CREATE POLICY "Users can update their own documents" ON documents
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

-- Policy for deleting documents (authenticated users can delete their own documents)
CREATE POLICY "Users can delete their own documents" ON documents
  FOR DELETE TO authenticated
  USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- Service role can still do everything
CREATE POLICY "Service role full access to documents" ON documents
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

-- Ensure RLS is enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
