'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface EmptyStateProps {
  onPromptSelect: (prompt: string) => void;
}

export default function EmptyState({ onPromptSelect }: EmptyStateProps) {
  const actionPrompts = [
    {
      title: 'Emails',
      prompt: 'Check my unread emails',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 001.11 0l7.89-4.26a2 2 0 012.22 0L21 8M5 12h14m-7-7l3 3m0 0l3-3" />
        </svg>
      ),
      color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
    },
    {
      title: 'Exam Prep',
      prompt: 'Help me study for my CS101 final',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0 13C4.168 5.477 5.754 5 7.5 5s3.332.477 4.5 1.253m0 13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13L8.25 3.433M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
    },
    {
      title: 'Career',
      prompt: "What's the job market for AI Engineers?",
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2H5a2 2 0 00-2 2v2m16 0v2a2 2 0 002 2h.01M5 20H4a2 2 0 01-2-2v-6a2 2 0 012-2h1m0 4V8a1 1 0 011-1h4a1 1 0 011 1v10m0-4a1 1 0 011 1h4a1 1 0 011-1v-10m6 0a2 2 0 002 2v10a2 2 0 002 2h.01" />
        </svg>
      ),
      color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
    },
    {
      title: 'Resources',
      prompt: 'Find me videos on Python list comprehension',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 001.555-.832V9.87a1 1 0 00-1.555-.832zM5 9.87v4.263a1 1 0 001.555.832l3.197 2.132a1 1 0 001.555 0l3.197-2.132a1 1 0 001.555-.832V9.87a1 1 0 00-1.555-.832L6.555 8.568A1 1 0 005 9.87z" />
        </svg>
      ),
      color: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300'
    }
  ];

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-4xl w-full">
        <Card className="p-8 text-center">
          <h1 className="text-3xl font-bold mb-4">
            Hello! How can I help you today?
          </h1>
          <p className="text-muted-foreground mb-8">
            Choose from the suggestions below or type your own question
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {actionPrompts.map((action, index) => (
              <Card
                key={index}
                className="p-6 cursor-pointer transition-all hover:shadow-md hover:scale-105 border border-border"
                onClick={() => onPromptSelect(action.prompt)}
              >
                <div className="flex flex-col items-center text-center space-y-4">
                  <div className={`p-3 rounded-full ${action.color}`}>
                    {action.icon}
                  </div>
                  <h3 className="font-semibold">{action.title}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {action.prompt}
                  </p>
                </div>
              </Card>
            ))}
          </div>

          <div className="mt-8 pt-6 border-t border-border">
            <p className="text-sm text-muted-foreground">
              You can also ask me anything about studying, coding, or career advice!
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}