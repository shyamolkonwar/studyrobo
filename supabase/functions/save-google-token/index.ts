import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

console.log("Save Google Token function loaded")

serve(async (req) => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  }

  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Create Supabase client with service role key for admin access
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Get the authorization header from the request
    const authHeader = req.headers.get('Authorization')!
    if (!authHeader) {
      throw new Error('No authorization header')
    }

    // Get the user from the JWT
    const token = authHeader.replace('Bearer ', '')
    const { data: { user }, error: userError } = await supabaseClient.auth.getUser(token)

    if (userError || !user) {
      throw new Error('Invalid token')
    }

    // Get the request body
    const { app_name, refresh_token } = await req.json()

    if (!app_name || !refresh_token) {
      throw new Error('Missing app_name or refresh_token')
    }

    // Insert the refresh token into the user_connections table
    // Note: In production, this should be encrypted with pgsodium
    const { data, error } = await supabaseClient
      .from('user_connections')
      .upsert({
        user_id: user.id,
        app_name: app_name,
        refresh_token: refresh_token
      }, {
        onConflict: 'user_id,app_name'
      })

    if (error) {
      throw new Error(`Failed to save connection: ${error.message}`)
    }

    return new Response(
      JSON.stringify({ message: 'Token saved successfully' }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      },
    )

  } catch (error) {
    console.error('Error in save-google-token function:', error)

    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : String(error) }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      },
    )
  }
})
