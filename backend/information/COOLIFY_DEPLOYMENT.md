# Coolify Docker Deployment Guide

This guide will help you deploy the StudyRobo application to your Hostinger VPS using Coolify.

## Prerequisites

- Hostinger VPS with Coolify installed
- Domain: `satro.space` (frontend) and `backend.satro.space` (backend)
- Supabase project with database and storage configured
- OpenAI API key
- Google OAuth credentials

## Project Structure

You have two separate projects:
- **Backend**: `backend.satro.space` (FastAPI)
- **Frontend**: `satro.space` (Next.js)

## Backend Deployment

### 1. Create Backend Project in Coolify

1. Go to your Coolify dashboard
2. Click "Add Project" → "Docker Compose"
3. Set project name: `studyrobo-backend`
4. Set domain: `backend.satro.space`

### 2. Upload Backend Files

Upload the entire `backend/` directory to Coolify, or connect your Git repository.

### 3. Environment Variables

Set these environment variables in Coolify:

```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# LLM Provider
LLM_PROVIDER=openai

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Frontend URL
FRONTEND_URL=https://satro.space

# Environment
ENVIRONMENT=production
PROJECT_NAME=StudyRobo API
API_V1_STR=/api/v1
```

### 4. Docker Compose Configuration

Use the `docker-compose.prod.yml` file for deployment.

### 5. Database Migration

After deployment, run the database migration:

```sql
-- Run this in your Supabase SQL Editor
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_index int;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS total_chunks int;
CREATE INDEX IF NOT EXISTS idx_documents_chunk_index ON documents(chunk_index);
CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);
```

## Frontend Deployment

### 1. Create Frontend Project in Coolify

1. Go to your Coolify dashboard
2. Click "Add Project" → "Docker Compose"
3. Set project name: `studyrobo-frontend`
4. Set domain: `satro.space`

### 2. Upload Frontend Files

Upload the entire `frontend/` directory to Coolify, or connect your Git repository.

### 3. Environment Variables

Set these environment variables in Coolify:

```bash
# Next.js Configuration
NODE_ENV=production

# API Configuration
NEXT_PUBLIC_API_URL=https://backend.satro.space

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Application Configuration
NEXT_PUBLIC_APP_NAME=StudyRobo
NEXT_PUBLIC_APP_URL=https://satro.space
```

### 4. Docker Compose Configuration

Use the `docker-compose.prod.yml` file for deployment.

## Deployment Steps

### Step 1: Deploy Backend

1. In Coolify, create the backend project
2. Upload/configure the backend code
3. Set environment variables
4. Deploy the backend service
5. Verify health check: `https://backend.satro.space/health`

### Step 2: Deploy Frontend

1. In Coolify, create the frontend project
2. Upload/configure the frontend code
3. Set environment variables (make sure `NEXT_PUBLIC_API_URL` points to backend)
4. Deploy the frontend service
5. Verify the app loads: `https://satro.space`

### Step 3: Configure SSL

Coolify should automatically handle SSL certificates for your domains. Make sure:
- `backend.satro.space` has SSL
- `satro.space` has SSL

### Step 4: Test the Application

1. Visit `https://satro.space`
2. Try logging in with Google OAuth
3. Upload a document (PDF/DOCX) with a course name
4. Ask questions in chat to test RAG functionality

## Troubleshooting

### Backend Issues

- Check logs in Coolify dashboard
- Verify environment variables are set correctly
- Ensure database connection works
- Check OpenAI API key is valid

### Frontend Issues

- Verify `NEXT_PUBLIC_API_URL` points to correct backend URL
- Check Supabase configuration
- Ensure Google OAuth redirect URIs include your domain

### Common Issues

1. **CORS errors**: Update CORS origins in `backend/app/main.py` to include your frontend domain
2. **Database connection**: Verify `DATABASE_URL` is correct
3. **File uploads**: Ensure Supabase storage bucket `user-documents` exists and is configured

## Monitoring

- Use Coolify's built-in monitoring
- Check application logs regularly
- Monitor database performance
- Set up alerts for downtime

## Updates

When deploying updates:

1. Push changes to your Git repository
2. Coolify will automatically rebuild and redeploy
3. Test thoroughly after each deployment
4. Run database migrations if schema changes

## Security Notes

- Never commit `.env` files to Git
- Use Coolify's secret management for sensitive data
- Regularly rotate API keys
- Keep dependencies updated
- Monitor for security vulnerabilities
