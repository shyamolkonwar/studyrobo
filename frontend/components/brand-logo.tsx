'use client';

import { Brain, CircuitBoard } from 'lucide-react';

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export default function BrandLogo({ size = 'md', showText = true, className = "" }: BrandLogoProps) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10'
  };

  const textSizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg'
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`relative ${sizeClasses[size]}`}>
        {/* Brain Icon */}
        <Brain
          className={`${sizeClasses[size]} text-brand-violet absolute inset-0`}
          strokeWidth={2}
        />
        {/* Circuit overlay */}
        <CircuitBoard
          className={`${sizeClasses[size]} text-brand-blue opacity-70 absolute inset-0 scale-90`}
          strokeWidth={1.5}
        />
      </div>
      {showText && (
        <span className={`font-bold font-heading ${textSizes[size]} text-foreground`}>
          Lemma
        </span>
      )}
    </div>
  );
}
