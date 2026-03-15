import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'News Aggregation Platform',
  description: 'Automated news aggregation, processing, and publishing platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
