-- Supabase Storage setup for user document uploads
-- Run this in Supabase SQL Editor

-- 1. Create storage bucket for user documents
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'user-documents',
  'user-documents',
  false, -- Private bucket
  10485760, -- 10MB limit
  ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
)
ON CONFLICT (id) DO NOTHING;

-- 2. Create policies for user document storage
-- Users can upload files to their own folder
CREATE POLICY "Users can upload to their own folder" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'user-documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Users can read their own files
CREATE POLICY "Users can read own files" ON storage.objects
  FOR SELECT TO authenticated
  USING (
    bucket_id = 'user-documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Users can update their own files
CREATE POLICY "Users can update own files" ON storage.objects
  FOR UPDATE TO authenticated
  USING (
    bucket_id = 'user-documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
  )
  WITH CHECK (
    bucket_id = 'user-documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Users can delete their own files
CREATE POLICY "Users can delete own files" ON storage.objects
  FOR DELETE TO authenticated
  USING (
    bucket_id = 'user-documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Service role can manage all files
CREATE POLICY "Service role full access to user documents" ON storage.objects
  FOR ALL TO service_role
  USING (bucket_id = 'user-documents')
  WITH CHECK (bucket_id = 'user-documents');

-- 3. Create function to handle document metadata after upload
CREATE OR REPLACE FUNCTION handle_document_upload()
RETURNS TRIGGER AS $$
DECLARE
  user_record RECORD;
  file_name TEXT;
  file_type TEXT;
  course_name TEXT;
BEGIN
  -- Extract user ID from folder path
  SELECT id INTO user_record
  FROM users
  WHERE google_id = (storage.foldername(NEW.name))[1];

  IF user_record.id IS NULL THEN
    RAISE EXCEPTION 'User not found for uploaded file';
  END IF;

  -- Extract file name and type
  file_name := (storage.filename(NEW.name))[1];
  file_type := CASE
    WHEN LOWER(RIGHT(file_name, 4)) = '.pdf' THEN 'pdf'
    WHEN LOWER(RIGHT(file_name, 5)) = '.docx' THEN 'docx'
    ELSE 'unknown'
  END;

  -- Get user's course name
  SELECT course_name INTO course_name
  FROM users
  WHERE id = user_record.id;

  -- Insert document record (embedding will be added by Edge Function)
  INSERT INTO documents (
    user_id,
    original_file_name,
    file_type,
    file_path,
    course_name,
    content
  ) VALUES (
    user_record.id,
    file_name,
    file_type,
    NEW.name,
    course_name,
    'Processing...' -- Placeholder content, will be updated by Edge Function
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Create trigger to handle document metadata after upload
-- Temporarily disabled to avoid database errors
-- DROP TRIGGER IF EXISTS on_document_upload ON storage.objects;
-- CREATE TRIGGER on_document_upload
--   AFTER INSERT ON storage.objects
--   FOR EACH ROW
--   WHEN (NEW.bucket_id = 'user-documents')
--   EXECUTE FUNCTION handle_document_upload();
