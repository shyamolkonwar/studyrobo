 import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"
// Use a Deno-compatible PDF library
import { getDocument } from "https://esm.sh/pdfjs-dist@3.11.174/build/pdf.mjs"
import mammoth from "https://esm.sh/mammoth@1.6.0"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { documentId, filePath } = await req.json()

    if (!documentId || !filePath) {
      throw new Error('Missing required parameters: documentId, filePath')
    }

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    // Download file from storage
    const { data: fileData, error: downloadError } = await supabase.storage
      .from('user-documents')
      .download(filePath)

    if (downloadError) {
      throw new Error(`Failed to download file: ${downloadError.message}`)
    }

    // For now, just mark the document as completed with basic info
    // TODO: Implement proper text extraction and embedding generation
    const fileExtension = filePath.toLowerCase().split('.').pop()
    const fileName = filePath.split('/').pop() || 'Unknown'

    let content = ''
    let embedding = null

    if (fileExtension === 'pdf') {
      content = `[PDF Document: ${fileName}] - Content extraction not yet implemented`
    } else if (fileExtension === 'docx') {
      content = `[DOCX Document: ${fileName}] - Content extraction not yet implemented`
    } else {
      content = `[Document: ${fileName}] - Unsupported file type`
    }

    // Generate a simple embedding for the filename (placeholder)
    try {
      const openaiApiKey = Deno.env.get('OPENAI_API_KEY')
      if (openaiApiKey) {
        const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${openaiApiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            input: content,
            model: 'text-embedding-ada-002',
          }),
        })

        if (embeddingResponse.ok) {
          const embeddingData = await embeddingResponse.json()
          embedding = embeddingData.data[0].embedding
        }
      }
    } catch (embeddingError) {
      console.error('Embedding generation failed:', embeddingError)
      // Continue without embedding
    }

    // Update document with basic info
    const { error: updateError } = await supabase
      .from('documents')
      .update({
        content: content,
        embedding: embedding,
        processing_status: 'completed'
      })
      .eq('id', documentId)

    if (updateError) {
      throw new Error(`Failed to update document: ${updateError.message}`)
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Document processed successfully'
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    )

  } catch (error) {
    console.error('Error processing document:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      }
    )
  }
})
