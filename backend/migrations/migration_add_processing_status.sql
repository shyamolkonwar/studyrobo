-- Add processing_status column to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status text DEFAULT 'completed';

-- Update existing documents to have completed status
UPDATE documents SET processing_status = 'completed' WHERE processing_status IS NULL;
