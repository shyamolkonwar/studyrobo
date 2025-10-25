# Google Login Setup with Supabase and Google Cloud Console

This guide explains how to set up Google OAuth login for the StudyRobo project using Supabase Auth and Google Cloud Console, according to the pivot.txt requirements.

## Prerequisites

- Google Cloud Console account
- Supabase account and project
- StudyRobo backend and frontend code

## Step 1: Set up Google Cloud Console

### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it
4. Enable the Gmail API (for email tools):
   - Search for "Gmail API" and enable it

### 1.2 Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Configure the OAuth consent screen if not done already:
   - User Type: External
   - App name: StudyRobo
   - User support email: your-email@example.com
   - Developer contact information: your-email@example.com
   - Add scopes: `.../auth/gmail.readonly`, `.../auth/gmail.compose`, `.../auth/spreadsheets.readonly`
4. Create OAuth client ID:
   - Application type: Web application
   - Name: StudyRobo Web Client
   - Authorized JavaScript origins: `http://localhost:3000` (for development)
   - Authorized redirect URIs:
     - `http://localhost:3000/auth/google/callback` (for custom implementation)
     - `https://your-project.supabase.co/auth/v1/callback` (for Supabase)

### 1.3 Get Your Credentials

After creating the OAuth client, note down:
- Client ID
- Client Secret

## Step 2: Set up Supabase Auth

### 2.1 Enable Google Provider in Supabase

1. Go to your Supabase project dashboard
2. Navigate to "Authentication" > "Providers"
3. Find "Google" and click to enable it
4. Enter your Google OAuth credentials:
   - Client ID: [Your Google Client ID]
   - Client Secret: [Your Google Client Secret]
5. Configure additional settings:
   - Redirect URLs: Add your frontend URLs
   - Enable the required scopes: `email`, `profile`, `https://www.googleapis.com/auth/gmail.readonly`, `https://www.googleapis.com/auth/gmail.compose`

### 2.2 Configure Supabase Auth Settings

1. In Supabase dashboard > "Authentication" > "Settings"
2. Configure:
   - Site URL: `http://localhost:3000` (for development)
   - Redirect URLs: Add your callback URLs
3. Enable email confirmations if desired
4. Set up additional auth providers if needed

### 2.3 Get Supabase Credentials

From your Supabase project settings:
- Project URL: `https://your-project-id.supabase.co`
- Anon/Public Key: `your-anon-key`
- Service Role Key: `your-service-role-key` (keep secret)

## Step 3: Backend Configuration

### 3.1 Install Supabase Python Client

Add to `backend/requirements.txt`:
```
supabase>=2.0.0
python-dotenv
```

### 3.2 Environment Variables

Create/update `backend/.env`:
```
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Google OAuth (for custom implementation if needed)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Database
DATABASE_URL=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres
```

### 3.3 Update Backend Auth Logic

Replace the custom Google OAuth implementation with Supabase Auth:

1. Create `backend/app/core/supabase_client.py`:
```python
from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
```

2. Update `backend/app/api/v1/endpoints/auth/google.py` to use Supabase Auth

3. Modify user creation and management to use Supabase users table

## Step 4: Frontend Configuration

### 4.1 Install Supabase JS Client

In `frontend/` directory:
```bash
npm install @supabase/supabase-js
```

### 4.2 Create Supabase Client

Create `frontend/lib/supabase.ts`:
```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 4.3 Environment Variables

Create/update `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4.4 Update Frontend Auth Logic

Replace custom login with Supabase Auth:

1. Update login to use `supabase.auth.signInWithOAuth({ provider: 'google' })`
2. Handle auth state changes with `supabase.auth.onAuthStateChange`
3. Get user session and tokens from Supabase
4. Update API calls to include Supabase JWT tokens

## Step 5: Database Schema Updates

### 5.1 Update Users Table

Since Supabase handles users, you may not need a separate users table, or sync Supabase users with your custom table.

### 5.2 Update Auth Flow

- Use Supabase user IDs instead of custom user IDs
- Store Google tokens in Supabase user metadata or separate table
- Update chat and message endpoints to work with Supabase auth

## Step 6: Testing

1. Start the backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. Test the login flow:
   - Click "Login with Google"
   - Complete OAuth flow
   - Verify user is authenticated
   - Test chat functionality with authenticated user

## Troubleshooting

### Common Issues:

1. **Redirect URI Mismatch**: Ensure all redirect URIs are correctly configured in both Google Cloud Console and Supabase
2. **Scopes Not Granted**: Make sure all required scopes are enabled in Google OAuth consent screen
3. **CORS Issues**: Configure CORS in Supabase dashboard for your frontend domain
4. **Token Storage**: Supabase handles token refresh automatically, but ensure proper session management

### Debug Tips:

- Check browser network tab for failed requests
- Use Supabase dashboard to monitor auth events
- Check server logs for authentication errors
- Verify environment variables are loaded correctly

## Security Notes

- Never commit secret keys to version control
- Use environment variables for all sensitive configuration
- Enable Row Level Security (RLS) in Supabase for data protection
- Regularly rotate OAuth client secrets
- Monitor authentication logs for suspicious activity

## Next Steps

After successful setup:
1. Implement user profile management
2. Add logout functionality
3. Handle token refresh scenarios
4. Add user-specific data isolation
5. Implement proper error handling for auth failures
