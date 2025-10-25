'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import LayoutWrapper from '@/components/layout-wrapper';
import { Calendar, CheckCircle, Clock, Target, TrendingUp, AlertCircle } from 'lucide-react';

interface AttendanceRecord {
  id: string;
  course_name: string;
  marked_at: string;
  date: string;
}

interface CourseSummary {
  course_name: string;
  total_attendance: number;
  last_marked: string;
  attendance_dates: string[];
}

interface AttendanceStats {
  total_attendance: number;
  total_courses: number;
  attendance_percentage: number;
  courses: CourseSummary[];
}

export default function AttendancePage() {
  const [user, setUser] = useState<any>(null);
  const [courseCode, setCourseCode] = useState('');
  const [isMarking, setIsMarking] = useState(false);
  const [attendanceStats, setAttendanceStats] = useState<AttendanceStats | null>(null);
  const [markStatus, setMarkStatus] = useState<{
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
      loadAttendanceStats();
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
              loadAttendanceStats();
            }
          });
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

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
        const stats = await response.json();
        setAttendanceStats(stats);
      }
    } catch (error) {
      console.error('Error loading attendance stats:', error);
    }
  };

  const markAttendance = async () => {
    if (!courseCode.trim()) {
      setMarkStatus({
        type: 'error',
        message: 'Please enter a course code'
      });
      return;
    }

    setIsMarking(true);
    setMarkStatus({ type: null, message: '' });

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      // For now, we'll use a simple API call to mark attendance
      // In a real implementation, this might integrate with a course management system
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/attendance/mark`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          course_name: courseCode.trim()
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setMarkStatus({
          type: 'success',
          message: `Successfully marked attendance for ${courseCode}`
        });
        setCourseCode('');

        // Reload stats
        setTimeout(() => {
          loadAttendanceStats();
        }, 1000);

      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to mark attendance');
      }
    } catch (error: any) {
      setMarkStatus({
        type: 'error',
        message: error.message || 'Failed to mark attendance'
      });
    } finally {
      setIsMarking(false);
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
            Mark Attendance
          </h1>
          <p className="text-muted-foreground">
            Keep track of your class attendance and monitor your academic progress
          </p>
        </div>

        {/* Mark Attendance Section */}
        <Card className="p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Calendar className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-semibold">Mark Today's Attendance</h2>
          </div>

          {/* Status Message */}
          {markStatus.type && (
            <Card className={`p-4 mb-4 ${markStatus.type === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
              <div className="flex items-center gap-2">
                {markStatus.type === 'success' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                )}
                <p className={`text-sm ${markStatus.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                  {markStatus.message}
                </p>
              </div>
            </Card>
          )}

          <div className="space-y-4">
            <div>
              <Label htmlFor="course-code">Course Code</Label>
              <Input
                id="course-code"
                placeholder="e.g., CS101, MATH201, PHYSICS101"
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && markAttendance()}
                disabled={isMarking}
              />
              <p className="text-sm text-muted-foreground mt-1">
                Enter the course code for the class you're attending
              </p>
            </div>

            <Button
              onClick={markAttendance}
              disabled={isMarking || !courseCode.trim()}
              className="w-full"
            >
              {isMarking ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                  Marking Attendance...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Mark Attendance
                </>
              )}
            </Button>
          </div>
        </Card>

        {/* Attendance Statistics */}
        <Card className="p-6 mb-8">
          <div className="flex items-center gap-3 mb-6">
            <Target className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-semibold">Your Attendance Overview</h2>
          </div>

          {attendanceStats ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              {/* Overall Percentage */}
              <Card className="p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <TrendingUp className="w-8 h-8 text-primary" />
                </div>
                <div className="text-3xl font-bold text-primary mb-1">
                  {attendanceStats.attendance_percentage}%
                </div>
                <p className="text-sm text-muted-foreground">Overall Attendance</p>
              </Card>

              {/* Total Classes */}
              <Card className="p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Calendar className="w-8 h-8 text-primary" />
                </div>
                <div className="text-3xl font-bold text-primary mb-1">
                  {attendanceStats.total_attendance}
                </div>
                <p className="text-sm text-muted-foreground">Classes Attended</p>
              </Card>

              {/* Total Courses */}
              <Card className="p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Clock className="w-8 h-8 text-primary" />
                </div>
                <div className="text-3xl font-bold text-primary mb-1">
                  {attendanceStats.total_courses}
                </div>
                <p className="text-sm text-muted-foreground">Active Courses</p>
              </Card>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Loading attendance statistics...</p>
            </div>
          )}

          {/* Course Breakdown */}
          {attendanceStats && attendanceStats.courses.length > 0 && (
            <div>
              <h3 className="text-lg font-medium mb-4">Course Breakdown</h3>
              <div className="space-y-4">
                {attendanceStats.courses.map((course, index) => (
                  <Card key={index} className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <h4 className="font-medium">{course.course_name}</h4>
                        <p className="text-sm text-muted-foreground">
                          Last marked: {new Date(course.last_marked).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-primary">
                          {course.total_attendance}
                        </div>
                        <p className="text-sm text-muted-foreground">classes</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* Quick Tips */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Attendance Tips</h2>
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <p>Mark your attendance immediately after class to maintain accurate records</p>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <p>Use consistent course codes to keep your records organized</p>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <p>Regular attendance tracking helps you maintain academic discipline</p>
            </div>
          </div>
        </Card>
      </div>
    </LayoutWrapper>
  );
}
