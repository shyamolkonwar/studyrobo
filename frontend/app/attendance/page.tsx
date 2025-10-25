'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Calendar } from '@/components/ui/calendar';
import LayoutWrapper from '@/components/layout-wrapper';
import { CalendarIcon, CheckCircle, Clock, Target, TrendingUp, AlertCircle, AlertTriangle } from 'lucide-react';
import { format, isSameDay } from 'date-fns';

interface AttendanceRecord {
  id: string;
  course_name: string;
  marked_at: string;
  date: string;
}

interface CourseBreakdown {
  course_name: string;
  percentage: number;
  ratio: string;
  status: string;
  allowed_absences_left: number;
}

interface AttendanceStats {
  target_attendance: number;
  overall_percentage: number;
  total_attended: number;
  total_possible: number;
  total_missed: number;
  allowed_absences_left: number;
  courses: CourseBreakdown[];
}

export default function AttendancePage() {
  const [user, setUser] = useState<any>(null);
  const [courseCode, setCourseCode] = useState('');
  const [targetAttendance, setTargetAttendance] = useState('');
  const [isMarking, setIsMarking] = useState(false);
  const [isSettingTarget, setIsSettingTarget] = useState(false);
  const [attendanceStats, setAttendanceStats] = useState<AttendanceStats | null>(null);
  const [attendanceRecords, setAttendanceRecords] = useState<AttendanceRecord[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [selectedDateCourses, setSelectedDateCourses] = useState<string[]>([]);
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
      loadAttendanceData();
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
              loadAttendanceData();
            }
          });
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  const loadAttendanceData = async () => {
    await Promise.all([loadAttendanceStats(), loadAttendanceRecords()]);
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
        const stats = await response.json();
        setAttendanceStats(stats);
        setTargetAttendance(stats.target_attendance.toString());
      }
    } catch (error) {
      console.error('Error loading attendance stats:', error);
    }
  };

  const loadAttendanceRecords = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/attendance/records`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setAttendanceRecords(data.records || []);
      }
    } catch (error) {
      console.error('Error loading attendance records:', error);
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

        // Reload data
        setTimeout(() => {
          loadAttendanceData();
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

  const setAttendanceTarget = async () => {
    const target = parseFloat(targetAttendance);
    if (isNaN(target) || target < 0 || target > 100) {
      setMarkStatus({
        type: 'error',
        message: 'Please enter a valid target percentage (0-100)'
      });
      return;
    }

    setIsSettingTarget(true);
    setMarkStatus({ type: null, message: '' });

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/attendance/target`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          target_attendance: target
        }),
      });

      if (response.ok) {
        setMarkStatus({
          type: 'success',
          message: `Target attendance set to ${target}%`
        });

        // Reload stats
        setTimeout(() => {
          loadAttendanceStats();
        }, 1000);

      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to set target');
      }
    } catch (error: any) {
      setMarkStatus({
        type: 'error',
        message: error.message || 'Failed to set target'
      });
    } finally {
      setIsSettingTarget(false);
    }
  };

  const getProgressColor = (percentage: number, target: number) => {
    if (percentage >= target) return 'bg-green-500';
    if (percentage >= target - 10) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getStatusBadgeVariant = (status: string) => {
    return status === 'Safe' ? 'default' : 'destructive';
  };

  const getAttendanceDates = () => {
    return attendanceRecords.map(record => new Date(record.date));
  };

  const handleDateSelect = (date: Date | undefined) => {
    setSelectedDate(date);
    if (date) {
      const coursesOnDate = attendanceRecords
        .filter(record => isSameDay(new Date(record.date), date))
        .map(record => record.course_name);
      setSelectedDateCourses(coursesOnDate);
    } else {
      setSelectedDateCourses([]);
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
      <div className="container mx-auto p-6 max-w-6xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold font-heading text-foreground mb-2">
            Attendance Manager
          </h1>
          <p className="text-muted-foreground">
            Track your attendance and stay on top of your academic goals
          </p>
        </div>

        {/* Action Bar */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Mark Attendance */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Mark Today's Attendance</h2>

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
                  placeholder="e.g., CS101, MATH201"
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && markAttendance()}
                  disabled={isMarking}
                />
              </div>

              <Button
                onClick={markAttendance}
                disabled={isMarking || !courseCode.trim()}
                className="w-full"
              >
                {isMarking ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                    Marking...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark Present
                  </>
                )}
              </Button>
            </div>
          </Card>

          {/* My Goal */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">My Goal</h2>

            <div className="space-y-4">
              <div>
                <Label htmlFor="target-attendance">My university requires...</Label>
                <div className="flex gap-2">
                  <Input
                    id="target-attendance"
                    type="number"
                    min="0"
                    max="100"
                    placeholder="75"
                    value={targetAttendance}
                    onChange={(e) => setTargetAttendance(e.target.value)}
                    disabled={isSettingTarget}
                  />
                  <span className="flex items-center text-sm text-muted-foreground">%</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  attendance to pass my courses
                </p>
              </div>

              <Button
                onClick={setAttendanceTarget}
                disabled={isSettingTarget || !targetAttendance.trim()}
                variant="outline"
                className="w-full"
              >
                {isSettingTarget ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                    Setting...
                  </>
                ) : (
                  <>
                    <Target className="w-4 h-4 mr-2" />
                    Set Target
                  </>
                )}
              </Button>
            </div>
          </Card>
        </div>

        {/* Dashboard */}
        <div className="space-y-8">
          {/* At-a-Glance Stats */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-6">Am I Safe?</h2>

            {attendanceStats ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Overall Attendance */}
                <Card className="p-4 text-center">
                  <div className="text-2xl font-bold mb-2">{attendanceStats.overall_percentage}%</div>
                  <Progress
                    value={attendanceStats.overall_percentage}
                    className={`mb-2 ${getProgressColor(attendanceStats.overall_percentage, attendanceStats.target_attendance)}`}
                  />
                  <p className="text-sm text-muted-foreground">Overall Attendance</p>
                </Card>

                {/* Total Classes Attended */}
                <Card className="p-4 text-center">
                  <div className="text-2xl font-bold mb-2">{attendanceStats.total_attended} / {attendanceStats.total_possible}</div>
                  <p className="text-sm text-muted-foreground">Classes Attended</p>
                </Card>

                {/* Total Classes Missed */}
                <Card className="p-4 text-center">
                  <div className="text-2xl font-bold mb-2">{attendanceStats.total_missed}</div>
                  <p className="text-sm text-muted-foreground">Classes Missed</p>
                </Card>

                {/* Allowed Absences Left */}
                <Card className="p-4 text-center">
                  <div className="text-2xl font-bold mb-2 text-red-600">{attendanceStats.allowed_absences_left}</div>
                  <p className="text-sm text-muted-foreground">Allowed Absences Left</p>
                </Card>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p>Loading attendance statistics...</p>
              </div>
            )}
          </Card>

          {/* Course Breakdown */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-6">Status by Course</h2>

            {attendanceStats && attendanceStats.courses.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Course</TableHead>
                    <TableHead>Percentage</TableHead>
                    <TableHead>Ratio</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {attendanceStats.courses.map((course, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{course.course_name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span>{course.percentage}%</span>
                          <Progress
                            value={course.percentage}
                            className="w-16 h-2"
                          />
                        </div>
                      </TableCell>
                      <TableCell>{course.ratio}</TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(course.status)}>
                          {course.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No course data available</p>
              </div>
            )}
          </Card>

          {/* Attendance Log */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-6">My Attendance Log</h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={handleDateSelect}
                  className="rounded-md border"
                  modifiers={{
                    attended: getAttendanceDates()
                  }}
                  modifiersStyles={{
                    attended: {
                      backgroundColor: '#22c55e',
                      color: 'white',
                      fontWeight: 'bold'
                    }
                  }}
                />
              </div>

              <div>
                {selectedDate && selectedDateCourses.length > 0 ? (
                  <div>
                    <h3 className="font-medium mb-4">
                      Attendance on {format(selectedDate, 'PPP')}
                    </h3>
                    <div className="space-y-2">
                      {selectedDateCourses.map((course, index) => (
                        <div key={index} className="flex items-center gap-2 p-2 bg-green-50 rounded">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span className="text-sm">{course}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : selectedDate ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No attendance recorded on {format(selectedDate, 'PPP')}</p>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <CalendarIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select a date to view attendance</p>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </LayoutWrapper>
  );
}
