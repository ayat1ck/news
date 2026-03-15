import React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  className?: string;
  children: React.ReactNode;
}

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-black text-white hover:bg-neutral-800',
  secondary: 'bg-neutral-100 text-neutral-900 hover:bg-neutral-200',
  outline: 'border border-neutral-200 hover:bg-neutral-50',
  ghost: 'hover:bg-neutral-100',
  danger: 'bg-red-50 text-red-600 hover:bg-red-100',
};

export function Button({ children, variant = 'primary', className = '', ...props }: ButtonProps) {
  return (
    <button
      className={`px-4 py-2 rounded-md font-medium transition-all flex items-center gap-2 disabled:opacity-50 whitespace-nowrap ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
