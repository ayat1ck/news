import { Suspense } from 'react';
import { HomeContent } from '@/components/public/HomeContent';

function HomeFallback() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <p className="text-neutral-500">Загрузка...</p>
    </div>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={<HomeFallback />}>
      <HomeContent />
    </Suspense>
  );
}
