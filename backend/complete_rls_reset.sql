-- Complete RLS reset for documents table - final fix
-- Run this in Supabase SQL Editor to completely reset all policies

-- Step 1: Drop ALL existing policies on documents table
DO $$
DECLARE
    policy_name TEXT;
BEGIN
    FOR policy_name IN
        SELECT p.polname
        FROM pg_policy p
        JOIN pg_class c ON p.polrelid = c.oid
        WHERE c.relname = 'documents'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON documents', policy_name);
    END LOOP;
END $$;

-- Step 2: Ensure RLS is enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Step 3: Create clean, working policies

-- Allow all authenticated users to read all documents (shared knowledge base)
CREATE POLICY "authenticated_read_all_documents" ON documents
  FOR SELECT TO authenticated
  USING (true);

-- Allow authenticated users to insert documents for themselves
CREATE POLICY "authenticated_insert_own_documents" ON documents
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- Allow users to update their own documents
CREATE POLICY "authenticated_update_own_documents" ON documents
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

-- Allow users to delete their own documents
CREATE POLICY "authenticated_delete_own_documents" ON documents
  FOR DELETE TO authenticated
  USING (
    user_id IN (
      SELECT id FROM users WHERE google_id = auth.uid()::text
    )
  );

-- Service role has full access
CREATE POLICY "service_role_full_access" ON documents
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);
