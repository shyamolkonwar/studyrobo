-- Final fix for document visibility - drop all policies and recreate clean ones

-- Drop ALL existing policies
DROP POLICY IF EXISTS "Authenticated users can read documents" ON documents;
DROP POLICY IF EXISTS "Authenticated users can read all documents" ON documents;
DROP POLICY IF EXISTS "Allow authenticated users to read documents" ON documents;

-- Create a simple read policy that allows all authenticated users to read all documents
CREATE POLICY "read_documents" ON documents
  FOR SELECT TO authenticated
  USING (true);

-- Ensure RLS is enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
