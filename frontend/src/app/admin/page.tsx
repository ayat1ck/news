'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Globe, Newspaper, ShieldCheck, CheckCircle2, PlayCircle, RefreshCw } from 'lucide-react';

interface DashboardStats {
  total_sources: number;
  active_sources: number;
  total_raw_items: number;
  new_raw_items: number;
  total_canonical_items: number;
  pending_moderation: number;
  published_items: number;
  duplicates_detected: number;
}

function StatCard({
  title,
  value,
  note,
  icon: Icon,
}: {
  title: string;
  value: number | string;
  note: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-start justify-between">
        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-2">
          <Icon className="h-5 w-5 text-neutral-600" />
        </div>
        <Badge variant="default">{note}</Badge>
      </div>
      <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-neutral-400">{title}</p>
      <h3 className="text-2xl font-bold">{value}</h3>
    </Card>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadStats = () => {
    apiFetch<DashboardStats>('/api/v1/dashboard/stats', { token })
      .then((response) => {
        setStats(response);
        setError('');
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    loadStats();
  }, []);

  const runOperation = async (path: string, key: string) => {
    setBusy(key);
    try {
      await apiFetch(path, { method: 'POST', token });
      window.setTimeout(loadStats, 1500);
    } finally {
      setBusy('');
    }
  };

  if (error) {
    return <div className="rounded-xl border border-red-100 bg-red-50 p-6 text-red-700">Ошибка: {error}</div>;
  }

  if (!stats) {
    return <div className="py-20 text-center text-neutral-500">Загрузка...</div>;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/collect-rss', 'collect-rss')}>
          <RefreshCw className="w-4 h-4" /> Collect RSS
        </Button>
        <Button variant="outline" disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/collect-telegram', 'collect-telegram')}>
          <RefreshCw className="w-4 h-4" /> Collect Telegram
        </Button>
        <Button disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/process', 'process')}>
          <PlayCircle className="w-4 h-4" /> Process raw items
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Источники" value={stats.total_sources} note={`${stats.active_sources} active`} icon={Globe} />
        <StatCard title="Сырые новости" value={stats.total_raw_items} note={`${stats.new_raw_items} new`} icon={Newspaper} />
        <StatCard title="Модерация" value={stats.pending_moderation} note="pending" icon={ShieldCheck} />
        <StatCard title="Опубликовано" value={stats.published_items} note={`${stats.total_canonical_items} canonical`} icon={CheckCircle2} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h4 className="text-lg font-bold">Текущий pipeline</h4>
          <div className="mt-5 space-y-4 text-sm text-neutral-600">
            <p>1. Собери новости кнопкой <span className="font-semibold text-neutral-900">Collect RSS</span> или через beat.</p>
            <p>2. Проверь новые записи в <span className="font-semibold text-neutral-900">Сырые новости</span>.</p>
            <p>3. Запусти <span className="font-semibold text-neutral-900">Process raw items</span>.</p>
            <p>4. Утверди статью в <span className="font-semibold text-neutral-900">Модерация</span>.</p>
            <p>5. Опубликуй её на сайт и/или в Telegram в <span className="font-semibold text-neutral-900">Каноничные</span>.</p>
          </div>
        </Card>

        <Card className="p-6">
          <h4 className="text-lg font-bold">Быстрый smoke test</h4>
          <div className="mt-5 space-y-4 text-sm text-neutral-600">
            <p>Добавь один RSS-источник с валидным feed URL.</p>
            <p>Нажми <span className="font-semibold text-neutral-900">Collect RSS</span>.</p>
            <p>Дождись появления raw items и нажми <span className="font-semibold text-neutral-900">Process raw items</span>.</p>
            <p>В модерации утверди статью.</p>
            <p>В canonical-списке опубликуй в website или Telegram.</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
