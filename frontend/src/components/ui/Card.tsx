import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={`bg-white border border-neutral-100 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow ${className}`}
    >
      {children}
    </div>
  );
}
