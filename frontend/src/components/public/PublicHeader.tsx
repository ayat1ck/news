'use client';

import Link from 'next/link';
import { Search, Menu } from 'lucide-react';

const CATEGORIES = ['Технологии', 'Бизнес', 'Наука', 'Дизайн', 'AI', 'Крипто'];

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-neutral-100">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-xl font-bold tracking-tighter cursor-pointer hover:opacity-80">
            NEWSFLUX
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-neutral-500">
            <Link href="/" className="hover:text-black transition-colors">
              Главная
            </Link>
            {CATEGORIES.slice(0, 4).map((item) => (
              <Link
                key={item}
                href={`/?category=${encodeURIComponent(item)}`}
                className="hover:text-black transition-colors"
              >
                {item}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative hidden sm:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Поиск новостей..."
              className="pl-10 pr-4 py-2 bg-neutral-100 border-none rounded-full text-sm w-48 lg:w-64 focus:ring-2 focus:ring-black/5 outline-none transition-all"
            />
          </div>
          <button type="button" className="w-6 h-6 md:hidden cursor-pointer" aria-label="Menu">
            <Menu className="w-6 h-6" />
          </button>
        </div>
      </div>
    </header>
  );
}
