'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import LayoutWrapper from '@/components/layout-wrapper';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';

interface UploadedDocument {
  id: string;
  filename: string;
  file_path: string;
  created_at: string;
  status: 'processing' | 'completed' | 'error';
}

export default function UploadPage() {
  const [user, setUser] = useState<any>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedDocument[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error' | null;
    message: string;
  }>({ type: null, message: '' });
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/auth/login');
        return;
      }

      // Check if user has completed onboarding
      try {
        const { data: userData, error } = await supabase
          .from('users')
          .select('onboarding_completed')
          .eq('google_id', session.user.id)
          .single();

        if (!userData?.onboarding_completed) {
          router.push('/onboarding');
          return;
        }
      } catch (error) {
        console.error('Error checking onboarding status:', error);
        router.push('/onboarding');
        return;
      }

      setUser(session.user);
      loadUserDocuments();
    };

    checkUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        router.push('/auth/login');
      } else {
        // Check onboarding status on auth state change
        supabase
          .from('users')
          .select('onboarding_completed')
          .eq('google_id', session.user.id)
          .single()
          .then(({ data: userData }) => {
            if (!userData?.onboarding_completed) {
              router.push('/onboarding');
            } else {
              setUser(session.user);
              loadUserDocuments();
            }
          });
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  const loadUserDocuments = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/user`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const documents = await response.json();
        setUploadedFiles(documents.map((doc: any) => ({
          id: doc.id,
          filename: doc.original_file_name || 'Unknown',
          file_path: doc.file_path,
          created_at: doc.created_at,
          status: doc.processing_status || 'completed'
        })));
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!allowedTypes.includes(file.type)) {
      setUploadStatus({
        type: 'error',
        message: 'Only PDF and DOCX files are allowed'
      });
      return;
    }

    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      setUploadStatus({
        type: 'error',
        message: 'File size must be less than 10MB'
      });
      return;
    }

    setIsUploading(true);
    setUploadStatus({ type: null, message: '' });

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setUploadStatus({
          type: 'success',
          message: `Successfully uploaded ${file.name}`
        });

        // Add to uploaded files list
        setUploadedFiles(prev => [{
          id: result.document_id,
          filename: file.name,
          file_path: result.file_path,
          created_at: new Date().toISOString(),
          status: 'processing'
        }, ...prev]);

        // Reload documents after a delay to show processing status
        setTimeout(() => {
          loadUserDocuments();
        }, 2000);

      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }
    } catch (error: any) {
      setUploadStatus({
        type: 'error',
        message: error.message || 'Upload failed'
      });
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (documentId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${documentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        setUploadedFiles(prev => prev.filter(doc => doc.id !== documentId));
        setUploadStatus({
          type: 'success',
          message: 'Document deleted successfully'
        });
      } else {
        throw new Error('Delete failed');
      }
    } catch (error: any) {
      setUploadStatus({
        type: 'error',
        message: error.message || 'Delete failed'
      });
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <LayoutWrapper>
      <div className="container mx-auto p-6 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold font-heading text-foreground mb-2">
            Upload Resources
          </h1>
          <p className="text-muted-foreground">
            Upload your study materials (PDFs and DOCX files) to enhance your AI assistant's knowledge
          </p>
        </div>

        {/* Upload Status */}
        {uploadStatus.type && (
          <Card className={`p-4 mb-6 ${uploadStatus.type === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
            <div className="flex items-center gap-2">
              {uploadStatus.type === 'success' ? (
                <CheckCircle className="w-5 h-5 text-green-600" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600" />
              )}
              <p className={`text-sm ${uploadStatus.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                {uploadStatus.message}
              </p>
            </div>
          </Card>
        )}

        {/* Upload Area */}
        <Card className="p-8 mb-8">
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Drop your files here</h3>
            <p className="text-muted-foreground mb-4">
              or click to browse. Supports PDF and DOCX files up to 10MB.
            </p>
            <Input
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileSelect}
              disabled={isUploading}
              className="hidden"
              id="file-upload"
            />
            <Button
              onClick={() => document.getElementById('file-upload')?.click()}
              disabled={isUploading}
              className="mx-auto"
            >
              {isUploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                  Uploading...
                </>
              ) : (
                'Choose File'
              )}
            </Button>
          </div>
        </Card>

        {/* Uploaded Documents */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Your Resources</h2>
          {uploadedFiles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No documents uploaded yet</p>
              <p className="text-sm mt-2">Upload your first study material above</p>
            </div>
          ) : (
            <div className="space-y-4">
              {uploadedFiles.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-8 h-8 text-primary" />
                    <div>
                      <h3 className="font-medium">{doc.filename}</h3>
                      <p className="text-sm text-muted-foreground">
                        Uploaded {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      doc.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : doc.status === 'processing'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {doc.status === 'processing' ? 'Processing...' : doc.status}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => deleteDocument(doc.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </LayoutWrapper>
  );
}
