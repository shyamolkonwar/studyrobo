-- Enable service role access to documents table
-- Run this in Supabase SQL Editor

-- Ensure service role can insert into documents table
CREATE POLICY "Service role full access to documents" ON documents
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

-- Ensure RLS is enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
