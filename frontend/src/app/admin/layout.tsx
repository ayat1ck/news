'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AdminSidebar } from '@/components/admin/AdminSidebar';
import { Badge } from '@/components/ui/Badge';
import { apiFetch } from '@/lib/api';
import { Search } from 'lucide-react';

type Identity = {
  email: string;
  role: string;
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const isLoginPage = pathname === '/admin/login';

  useEffect(() => {
    const host = window.location.hostname;
    const adminHost = process.env.NEXT_PUBLIC_ADMIN_HOST;
    const isAdminSubdomain = Boolean(adminHost && host === adminHost);
    const loginPath = isAdminSubdomain ? '/login' : '/admin/login';
    const homePath = isAdminSubdomain ? '/' : '/admin';
    const token = window.localStorage.getItem('token');

    if (!token && !isLoginPage) {
      router.replace(loginPath);
      return;
    }

    if (token && isLoginPage) {
      router.replace(homePath);
      return;
    }

    if (token) {
      apiFetch<Identity>('/api/v1/auth/me', { token })
        .then(setIdentity)
        .catch(() => {
          window.localStorage.removeItem('token');
          router.replace(loginPath);
        })
        .finally(() => setReady(true));
      return;
    }

    setReady(true);
  }, [isLoginPage, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50">
        <p className="text-neutral-500">Загрузка...</p>
      </div>
    );
  }

  if (isLoginPage) {
    return <main className="min-h-screen bg-neutral-50">{children}</main>;
  }

  const pageTitles: Record<string, string> = {
    '/admin': 'Обзор системы',
    '/admin/sources': 'Источники',
    '/admin/raw-news': 'Сырые новости',
    '/admin/canonical': 'Каноничные',
    '/admin/moderation': 'Модерация',
    '/admin/publishing': 'Публикации',
    '/admin/settings': 'Настройки',
  };
  const title = pageTitles[pathname] ?? 'Админ';

  return (
    <div className="flex min-h-screen bg-neutral-50/30">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-neutral-100 bg-white px-8">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-bold">{title}</h2>
            <Badge variant="success">Online</Badge>
          </div>
          <div className="flex items-center gap-6">
            <div className="relative hidden lg:block">
              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-400" />
              <input
                placeholder="Быстрый поиск..."
                className="w-64 rounded-lg border border-neutral-200 bg-neutral-50 py-1.5 pl-9 pr-4 text-xs outline-none focus:ring-1 focus:ring-black/10"
              />
            </div>
            <div className="flex items-center gap-3 border-l border-neutral-100 pl-6">
              <div className="hidden text-right sm:block">
                <p className="text-xs font-bold leading-none">{identity?.email || 'Admin'}</p>
                <p className="mt-1 text-[10px] uppercase text-neutral-400">{identity?.role || 'user'}</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-neutral-900" />
              <button
                type="button"
                onClick={() => {
                  window.localStorage.removeItem('token');
                  const host = window.location.hostname;
                  const adminHost = process.env.NEXT_PUBLIC_ADMIN_HOST;
                  router.replace(adminHost && host === adminHost ? '/login' : '/admin/login');
                }}
                className="text-xs text-neutral-500 hover:text-black"
              >
                Выйти
              </button>
            </div>
          </div>
        </header>
        <div className="mx-auto max-w-7xl p-8">{children}</div>
      </main>
    </div>
  );
}
