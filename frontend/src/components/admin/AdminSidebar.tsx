'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutGrid,
  Globe,
  Database,
  FileText,
  ShieldCheck,
  History,
  Settings,
  ExternalLink,
} from 'lucide-react';

const menuItems = [
  { href: '/admin', id: 'dash', label: 'Дашборд', icon: LayoutGrid },
  { href: '/admin/sources', id: 'sources', label: 'Источники', icon: Globe },
  { href: '/admin/raw-news', id: 'raw', label: 'Сырые новости', icon: Database },
  { href: '/admin/canonical', id: 'canonical', label: 'Каноничные', icon: FileText },
  { href: '/admin/moderation', id: 'mod', label: 'Модерация', icon: ShieldCheck },
  { href: '/admin/publishing', id: 'history', label: 'История', icon: History },
  { href: '/admin/settings', id: 'settings', label: 'Настройки', icon: Settings },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-neutral-100 h-screen sticky top-0 bg-white flex flex-col p-4">
      <div className="flex items-center gap-3 px-2 mb-8 mt-2">
        <div className="w-8 h-8 bg-black rounded flex items-center justify-center text-white font-bold">NF</div>
        <span className="font-bold tracking-tight text-lg">Console v1.0</span>
      </div>
      <nav className="flex-1 flex flex-col gap-1">
        {menuItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/admin' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.id}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive ? 'bg-neutral-100 text-black' : 'text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900'
              }`}
            >
              <item.icon className={`w-4 h-4 ${isActive ? 'text-black' : 'text-neutral-400'}`} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-4 border-t border-neutral-100">
        <Link
          href="/"
          className="flex items-center justify-between w-full px-3 py-2 text-sm text-neutral-500 hover:text-black transition-colors"
        >
          <span>На сайт</span>
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>
    </aside>
  );
}
