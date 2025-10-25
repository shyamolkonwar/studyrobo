-- Fix document visibility for authenticated users
-- Run this in Supabase SQL Editor

-- Allow all authenticated users to read all documents
CREATE POLICY "Allow authenticated users to read documents" ON documents
  FOR SELECT TO authenticated
  USING (true);

-- Ensure RLS is enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
