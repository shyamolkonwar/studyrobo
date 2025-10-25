import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"
import mammoth from "https://esm.sh/mammoth@1.6.0"
import * as pdfjsLib from "npm:pdfjs-dist"

// Simple text splitter implementation
class SimpleTextSplitter {
  constructor(private chunkSize: number, private chunkOverlap: number) {}

  splitText(text: string): string[] {
    const chunks: string[] = []
    let start = 0

    while (start < text.length) {
      let end = start + this.chunkSize
      if (end > text.length) {
        end = text.length
      }

      chunks.push(text.slice(start, end))
      start = end - this.chunkOverlap

      if (start >= text.length) break
    }

    return chunks
  }
}

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

    // Extract text content from the file
    const fileExtension = filePath.toLowerCase().split('.').pop()
    const fileName = filePath.split('/').pop() || 'Unknown'

    let content = ''
    let embedding = null

    try {
      if (fileExtension === 'pdf') {
        // Extract text from PDF
        const arrayBuffer = await fileData.arrayBuffer()
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
        const numPages = pdf.numPages

        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
          const page = await pdf.getPage(pageNum)
          const textContent = await page.getTextContent()
          const pageText = textContent.items.map((item: any) => item.str).join(' ')
          content += pageText + '\n'
        }

        if (!content.trim()) {
          content = `[PDF Document: ${fileName}] - No text content could be extracted from this PDF`
        }

      } else if (fileExtension === 'docx') {
        // Extract text from DOCX
        const arrayBuffer = await fileData.arrayBuffer()
        const result = await mammoth.extractRawText({ arrayBuffer })
        content = result.value

        if (!content.trim()) {
          content = `[DOCX Document: ${fileName}] - No text content could be extracted from this DOCX file`
        }

      } else {
        content = `[Document: ${fileName}] - Unsupported file type: ${fileExtension}`
      }
    } catch (extractionError) {
      console.error('Text extraction failed:', extractionError)
      const errorMessage = extractionError instanceof Error ? extractionError.message : String(extractionError)
      content = `[Document: ${fileName}] - Error extracting text: ${errorMessage}`
    }

    // Generate embedding for the content using text splitting
    try {
      const openaiApiKey = Deno.env.get('OPENAI_API_KEY')
      if (openaiApiKey && content.trim()) {
        // Split text into chunks
        const splitter = new SimpleTextSplitter(1000, 200)
        const chunks = splitter.splitText(content)

        // Generate embeddings for chunks
        const chunkEmbeddings = []
        for (const chunk of chunks) {
          const response = await fetch('https://api.openai.com/v1/embeddings', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${openaiApiKey}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              input: chunk,
              model: 'text-embedding-3-small',
            }),
          })

          if (response.ok) {
            const data = await response.json()
            chunkEmbeddings.push(data.data[0].embedding)
          }
        }

        // Average the embeddings
        if (chunkEmbeddings.length > 0) {
          const embeddingDim = chunkEmbeddings[0].length
          embedding = new Array(embeddingDim).fill(0)
          for (const chunkEmbedding of chunkEmbeddings) {
            for (let i = 0; i < embeddingDim; i++) {
              embedding[i] += chunkEmbedding[i]
            }
          }
          for (let i = 0; i < embeddingDim; i++) {
            embedding[i] /= chunkEmbeddings.length
          }
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
    const errorMessage = error instanceof Error ? error.message : String(error)
    return new Response(
      JSON.stringify({ error: errorMessage }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      }
    )
  }
})
