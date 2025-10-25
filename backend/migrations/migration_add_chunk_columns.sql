-- Add chunk columns to documents table for new RAG system
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_index int;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS total_chunks int;

-- Add index for chunk queries
CREATE INDEX IF NOT EXISTS idx_documents_chunk_index ON documents(chunk_index);
CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);
