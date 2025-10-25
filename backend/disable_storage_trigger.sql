-- Disable the problematic storage trigger
-- Run this in Supabase SQL Editor to temporarily disable the document upload trigger

-- Drop the trigger that causes database errors
DROP TRIGGER IF EXISTS on_document_upload ON storage.objects;

-- The trigger function is kept for future use, but the trigger is disabled
-- When ready to re-enable, uncomment the CREATE TRIGGER statement below:
-- CREATE TRIGGER on_document_upload
--   AFTER INSERT ON storage.objects
--   FOR EACH ROW
--   WHEN (NEW.bucket_id = 'user-documents')
--   EXECUTE FUNCTION handle_document_upload();
