'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  MessageSquare,
  Upload,
  CheckSquare,
  BookOpen,
  Mail,
  Calendar,
  TrendingUp,
  Clock,
  Users,
  FileText,
  Trash2,
  Loader2,
  Plus,
  Brain,
  Target,
  Award,
  Zap
} from 'lucide-react';

interface UserDocument {
  id: string;
  original_file_name: string;
  file_type: string;
  created_at: string;
}

interface GmailInfo {
  unreadCount: number;
  recentEmails: Array<{
    subject: string;
    from: string;
  }>;
}

interface AttendanceRecord {
  total_classes: number;
  attended_classes: number;
  percentage: number;
}

export default function DashboardWidgets() {
  const [user, setUser] = useState<any>(null);
  const [userDocuments, setUserDocuments] = useState<UserDocument[]>([]);
  const [gmailInfo, setGmailInfo] = useState<GmailInfo | null>(null);
  const [attendance, setAttendance] = useState<AttendanceRecord | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [courseCode, setCourseCode] = useState('');
  const [isMarkingAttendance, setIsMarkingAttendance] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setUser(session.user);
      }
    };
    getUser();
  }, []);

  useEffect(() => {
    if (user) {
      loadUserDocuments();
      checkGmailConnection();
      loadAttendanceStats();
    }
  }, [user]);

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
        const data = await response.json();
        setUserDocuments(data);
      }
    } catch (error) {
      console.error('Error loading user documents:', error);
    }
  };

  const checkGmailConnection = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/gmail/info`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setGmailInfo(data);
      }
    } catch (error) {
      console.error('Error checking Gmail connection:', error);
    }
  };

  const loadAttendanceStats = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/attendance/stats`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setAttendance(data);
      }
    } catch (error) {
      console.error('Error loading attendance stats:', error);
    }
  };

  const handleFileUpload = async () => {
    if (!uploadFile) return;

    setIsUploading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error('No session');

      const formData = new FormData();
      formData.append('file', uploadFile);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setUploadFile(null);
        loadUserDocuments();
        alert('Document uploaded successfully!');
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleMarkAttendance = async () => {
    if (!courseCode.trim()) {
      alert('Please enter a course code');
      return;
    }

    setIsMarkingAttendance(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error('No session');

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/attendance/mark`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ course_name: courseCode }),
      });

      if (response.ok) {
        setCourseCode('');
        loadAttendanceStats();
        alert('Attendance marked successfully!');
      } else {
        throw new Error('Failed to mark attendance');
      }
    } catch (error) {
      console.error('Error marking attendance:', error);
      alert('Failed to mark attendance');
    } finally {
      setIsMarkingAttendance(false);
    }
  };

  const createNewChat = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ title: 'New Chat' }),
      });

      if (response.ok) {
        const data = await response.json();
        router.push(`/chat/${data.conversation_id}`);
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
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
        loadUserDocuments();
      }
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Widget 1: Quick Actions */}
      <Card className="p-6 animate-slide-up">
        <h3 className="text-lg font-semibold font-heading mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-brand-violet" />
          Quick Actions
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Button
            onClick={() => router.push('/chat/new')}
            className="h-16 text-lg font-body"
            variant="brand"
            size="lg"
          >
            <MessageSquare className="w-5 h-5 mr-2" />
            Chat with Assistant
          </Button>

          <Button
            onClick={() => router.push('/upload')}
            variant="accent"
            className="h-16 text-lg font-body"
            size="lg"
          >
            <Upload className="w-5 h-5 mr-2" />
            Upload Resource
          </Button>

          <Button
            onClick={() => router.push('/attendance')}
            variant="success"
            className="h-16 text-lg font-body"
            size="lg"
          >
            <CheckSquare className="w-5 h-5 mr-2" />
            Mark Attendance
          </Button>
        </div>
      </Card>

      {/* Widget 2: My Library */}
      <Card id="library-widget" className="p-6 animate-slide-up" style={{ animationDelay: "0.1s" }}>
        <h3 className="text-lg font-semibold font-heading mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-brand-violet" />
          My Library
        </h3>
        {userDocuments.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground font-body">
              No documents uploaded yet. Upload your first resource to get started!
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {userDocuments.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors animate-fade-in">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-background rounded-lg">
                    <FileText className={`w-5 h-5 ${doc.file_type === 'pdf' ? 'text-brand-red' : 'text-brand-blue'}`} />
                  </div>
                  <div>
                    <p className="font-medium font-heading text-sm">{doc.original_file_name}</p>
                    <p className="text-sm text-muted-foreground font-body">
                      Uploaded {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deleteDocument(doc.id)}
                  className="hover:bg-brand-red/10"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Widget 3: Proactive Mentor */}
        <Card className="p-6 animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <h3 className="text-lg font-semibold font-heading mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-brand-violet" />
            What's on your mind?
          </h3>
          <div className="space-y-3">
            {gmailInfo && (
              <div className="flex items-center space-x-3 p-3 bg-brand-blue/10 rounded-lg border border-brand-blue/20">
                <Mail className="w-4 h-4 text-brand-blue" />
                <p className="text-sm font-body">
                  You have <span className="font-semibold">{gmailInfo.unreadCount}</span> unread emails from professors
                </p>
              </div>
            )}
            <div className="flex items-center space-x-3 p-3 bg-brand-green/10 rounded-lg border border-brand-green/20">
              <Award className="w-4 h-4 text-brand-green" />
              <p className="text-sm font-body">Keep up the great work with your studies!</p>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-brand-violet/10 rounded-lg border border-brand-violet/20">
              <Target className="w-4 h-4 text-brand-violet" />
              <p className="text-sm font-body">Try uploading today's lecture notes for better AI assistance</p>
            </div>
          </div>
        </Card>

        {/* Widget 4: Attendance Tracker */}
        <Card id="attendance-widget" className="p-6 animate-slide-up" style={{ animationDelay: "0.3s" }}>
          <h3 className="text-lg font-semibold font-heading mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-brand-green" />
            My Attendance
          </h3>
          {attendance ? (
            <div className="space-y-4">
              <div className="text-center">
                <div className={`text-4xl font-bold font-heading ${
                  attendance.percentage >= 80 ? 'text-brand-green' :
                  attendance.percentage >= 60 ? 'text-brand-yellow' : 'text-brand-red'
                }`}>
                  {attendance.percentage}%
                </div>
                <p className="text-sm text-muted-foreground font-body">Overall Attendance</p>
              </div>
              <div className="w-full bg-muted rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all duration-500 ${
                    attendance.percentage >= 80 ? 'bg-brand-green' :
                    attendance.percentage >= 60 ? 'bg-brand-yellow' : 'bg-brand-red'
                  }`}
                  style={{ width: `${attendance.percentage}%` }}
                ></div>
              </div>
              <p className="text-sm text-center text-muted-foreground font-body">
                You've attended <span className="font-semibold">{attendance.attended_classes}</span> out of{' '}
                <span className="font-semibold">{attendance.total_classes}</span> classes
              </p>
            </div>
          ) : (
            <div className="text-center py-4">
              <TrendingUp className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground font-body">No attendance records yet</p>
            </div>
          )}
        </Card>

        {/* Widget 5: Connected Apps */}
        <Card id="apps-widget" className="p-6 animate-slide-up" style={{ animationDelay: "0.4s" }}>
          <h3 className="text-lg font-semibold font-heading mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-brand-blue" />
            My Connections
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className={`text-center p-4 rounded-lg border transition-all ${
              gmailInfo
                ? 'border-brand-green bg-brand-green/10'
                : 'border-border bg-muted hover:bg-muted/80'
            }`}>
              <Mail className={`w-8 h-8 mx-auto mb-2 ${
                gmailInfo ? 'text-brand-green' : 'text-muted-foreground'
              }`} />
              <p className="text-sm font-medium font-heading mt-1">Gmail</p>
              {gmailInfo ? (
                <Badge variant="default" className="mt-2 bg-brand-green">Connected</Badge>
              ) : (
                <Button size="sm" variant="outline" className="mt-2">Connect</Button>
              )}
            </div>
            <div className="text-center p-4 rounded-lg border border-border bg-muted hover:bg-muted/80 transition-all">
              <Calendar className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm font-medium font-heading mt-1">Calendar</p>
              <Button size="sm" variant="outline" className="mt-2">Connect</Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Widget 6: Today's Agenda */}
      <Card className="p-6 animate-slide-up" style={{ animationDelay: "0.5s" }}>
        <h3 className="text-lg font-semibold font-heading mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-brand-blue" />
          Today's Schedule
        </h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-4 p-3 hover:bg-muted rounded-lg transition-colors">
            <span className="text-sm font-semibold font-heading text-brand-blue min-w-fit">10:00 AM</span>
            <div className="w-8 h-8 bg-brand-blue/10 rounded-full flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-brand-blue" />
            </div>
            <div>
              <p className="font-medium font-heading">CS101 Lecture</p>
              <p className="text-sm text-muted-foreground font-body">Room 301</p>
            </div>
          </div>
          <div className="flex items-center space-x-4 p-3 hover:bg-muted rounded-lg transition-colors">
            <span className="text-sm font-semibold font-heading text-brand-yellow min-w-fit">12:00 PM</span>
            <div className="w-8 h-8 bg-brand-yellow/10 rounded-full flex items-center justify-center">
              <Users className="w-4 h-4 text-brand-yellow" />
            </div>
            <div>
              <p className="font-medium font-heading">Lunch Break</p>
              <p className="text-sm text-muted-foreground font-body">Campus Cafeteria</p>
            </div>
          </div>
          <div className="flex items-center space-x-4 p-3 hover:bg-muted rounded-lg transition-colors">
            <span className="text-sm font-semibold font-heading text-brand-violet min-w-fit">3:00 PM</span>
            <div className="w-8 h-8 bg-brand-violet/10 rounded-full flex items-center justify-center">
              <Brain className="w-4 h-4 text-brand-violet" />
            </div>
            <div>
              <p className="font-medium font-heading">Study Session</p>
              <p className="text-sm text-muted-foreground font-body">Library</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
