'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import LayoutWrapper from '@/components/layout-wrapper';
import BrandLogo from '@/components/brand-logo';
import { Brain, GraduationCap, Clock } from 'lucide-react';

export default function Onboarding() {
  const [user, setUser] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    courseName: '',
    major: '',
    university: '',
    semester: ''
  });
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/auth/login');
        return;
      }

      // Check if user has already completed onboarding
      try {
        const { data: userData, error } = await supabase
          .from('users')
          .select('onboarding_completed')
          .eq('google_id', session.user.id)
          .single();

        if (userData?.onboarding_completed) {
          router.push('/');
          return;
        }
      } catch (error) {
        console.error('Error checking onboarding status:', error);
      }

      setUser(session.user);
    };

    checkUser();
  }, [router]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.courseName || !formData.major || !formData.university || !formData.semester) {
      alert('Please fill in all fields');
      return;
    }

    setIsSubmitting(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('No session found');
      }

      // Call the database function to complete onboarding
      const { error } = await supabase.rpc('complete_user_onboarding', {
        p_google_id: session.user.id,
        p_course_name: formData.courseName,
        p_major: formData.major,
        p_university: formData.university,
        p_semester: formData.semester
      });

      if (error) {
        throw error;
      }

      // Redirect to dashboard
      router.push('/');
    } catch (error) {
      console.error('Error completing onboarding:', error);
      alert('Failed to complete onboarding. Please try again.');
    } finally {
      setIsSubmitting(false);
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
      <div className="min-h-screen bg-gradient-to-br from-brand-blue/5 via-brand-violet/5 to-brand-green/5 flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8 space-y-6 animate-scale-in border border-brand-blue/20 shadow-lg">
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <BrandLogo size="lg" />
          </div>
          <div>
            <h1 className="text-3xl font-bold font-heading text-foreground">Welcome to Lemma!</h1>
            <p className="text-muted-foreground font-body mt-2">
              Let's set up your personalized learning experience
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="courseName" className="block text-sm font-semibold font-heading text-foreground mb-2 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-brand-violet" />
              Course Name
            </label>
            <Input
              id="courseName"
              name="courseName"
              type="text"
              placeholder="e.g., Computer Science 101"
              value={formData.courseName}
              onChange={handleInputChange}
              required
              className="font-body"
            />
          </div>

          <div>
            <label htmlFor="major" className="block text-sm font-semibold font-heading text-foreground mb-2 flex items-center gap-2">
              <Brain className="w-4 h-4 text-brand-blue" />
              Major
            </label>
            <Input
              id="major"
              name="major"
              type="text"
              placeholder="e.g., Computer Science"
              value={formData.major}
              onChange={handleInputChange}
              required
              className="font-body"
            />
          </div>

          <div>
            <label htmlFor="university" className="block text-sm font-semibold font-heading text-foreground mb-2 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-brand-green" />
              University
            </label>
            <Input
              id="university"
              name="university"
              type="text"
              placeholder="e.g., Stanford University"
              value={formData.university}
              onChange={handleInputChange}
              required
              className="font-body"
            />
          </div>

          <div>
            <label htmlFor="semester" className="block text-sm font-semibold font-heading text-foreground mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand-yellow" />
              Current Semester
            </label>
            <Input
              id="semester"
              name="semester"
              type="text"
              placeholder="e.g., Fall 2024"
              value={formData.semester}
              onChange={handleInputChange}
              required
              className="font-body"
            />
          </div>

          <Button
            type="submit"
            className="w-full font-semibold font-heading"
            variant="brand"
            size="lg"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                Setting up...
              </>
            ) : (
              'Complete Setup'
            )}
          </Button>
        </form>

        <div className="text-center text-sm text-muted-foreground">
          <p className="font-body">This information helps us personalize your learning experience</p>
        </div>
      </Card>
      </div>
    </LayoutWrapper>
  );
}