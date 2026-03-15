'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api';

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
};

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = await apiFetch<TokenResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: { email, password },
      });
      window.localStorage.setItem('token', data.access_token);
      const host = window.location.hostname;
      const adminHost = process.env.NEXT_PUBLIC_ADMIN_HOST;
      router.replace(adminHost && host === adminHost ? '/' : '/admin');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 p-4">
      <div className="w-full max-w-md bg-white border border-neutral-100 rounded-2xl shadow-sm p-8">
        <p className="text-neutral-400 text-xs font-bold uppercase tracking-widest mb-2">Доступ в консоль</p>
        <h1 className="text-2xl font-bold mb-2">Вход в Newsflux Console</h1>
        <p className="text-neutral-500 text-sm mb-6 leading-relaxed">
          Используйте учётные данные администратора. Для локальной разработки данные по умолчанию уже подставлены.
        </p>
        <div className="mb-6 rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-600">
          <p className="font-semibold text-neutral-900">Скрытый вход в консоль</p>
          <p className="mt-1">Локально: <span className="font-mono">/console</span> или <span className="font-mono">/admin/login</span>. В production: отдельный admin subdomain и путь <span className="font-mono">/login</span>.</p>
          <p className="mt-2">Локальные данные по умолчанию: <span className="font-mono">admin@example.com</span> / <span className="font-mono">admin123</span></p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full px-4 py-3 bg-neutral-50 border border-neutral-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-black/10 focus:border-neutral-300"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">
              Пароль
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full px-4 py-3 bg-neutral-50 border border-neutral-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-black/10 focus:border-neutral-300"
            />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-black text-white font-bold rounded-xl hover:bg-neutral-800 transition-colors disabled:opacity-50"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
