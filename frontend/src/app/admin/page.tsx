'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, Globe, Newspaper, PlayCircle, RefreshCw, ShieldCheck } from 'lucide-react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';

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
  const [feedback, setFeedback] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadStats = () => {
    apiFetch<DashboardStats>('/api/v1/dashboard/stats', { token })
      .then((response) => {
        setStats(response);
        setError('');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить статистику.'));
  };

  useEffect(() => {
    loadStats();
  }, []);

  const runOperation = async (path: string, key: string) => {
    setBusy(key);
    setFeedback('');
    try {
      await apiFetch(path, { method: 'POST', token });
      setFeedback('Операция запущена.');
      window.setTimeout(loadStats, 1500);
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Не удалось запустить операцию.');
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
      {feedback && (
        <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-700">
          {feedback}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/collect-rss', 'collect-rss')}>
          <RefreshCw className={`h-4 w-4 ${busy === 'collect-rss' ? 'animate-spin' : ''}`} /> Собрать RSS
        </Button>
        <Button variant="outline" disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/collect-telegram', 'collect-telegram')}>
          <RefreshCw className={`h-4 w-4 ${busy === 'collect-telegram' ? 'animate-spin' : ''}`} /> Собрать Telegram
        </Button>
        <Button variant="outline" disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/collect-vk', 'collect-vk')}>
          <RefreshCw className={`h-4 w-4 ${busy === 'collect-vk' ? 'animate-spin' : ''}`} /> Собрать VK
        </Button>
        <Button disabled={Boolean(busy)} onClick={() => runOperation('/api/v1/operations/process', 'process')}>
          <PlayCircle className={`h-4 w-4 ${busy === 'process' ? 'animate-pulse' : ''}`} /> Запустить pipeline
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Источники" value={stats.total_sources} note={`${stats.active_sources} активных`} icon={Globe} />
        <StatCard title="Сырые новости" value={stats.total_raw_items} note={`${stats.new_raw_items} новых`} icon={Newspaper} />
        <StatCard title="Модерация" value={stats.pending_moderation} note="ожидают" icon={ShieldCheck} />
        <StatCard title="Опубликовано" value={stats.published_items} note={`${stats.total_canonical_items} каноничных`} icon={CheckCircle2} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h4 className="text-lg font-bold">Текущий pipeline</h4>
          <div className="mt-5 space-y-4 text-sm text-neutral-600">
            <p>1. Собери новости кнопками <span className="font-semibold text-neutral-900">Собрать RSS</span>, <span className="font-semibold text-neutral-900">Собрать Telegram</span> или <span className="font-semibold text-neutral-900">Собрать VK</span>.</p>
            <p>2. Проверь новые записи в разделе <span className="font-semibold text-neutral-900">Сырые новости</span>.</p>
            <p>3. Запусти <span className="font-semibold text-neutral-900">pipeline</span>.</p>
            <p>4. Проверь и утверди статью в разделе <span className="font-semibold text-neutral-900">Модерация</span>.</p>
            <p>5. Публикуй сначала на сайт, а Telegram используй как дополнительный канал.</p>
          </div>
        </Card>

        <Card className="p-6">
          <h4 className="text-lg font-bold">Быстрая проверка</h4>
          <div className="mt-5 space-y-4 text-sm text-neutral-600">
            <p>Добавь RSS, Telegram или VK источник с валидными данными.</p>
            <p>Нажми соответствующую кнопку сбора.</p>
            <p>Дождись raw items и запусти <span className="font-semibold text-neutral-900">pipeline</span>.</p>
            <p>В модерации утверди статью.</p>
            <p>В каноничных материалах опубликуй на сайт, а Telegram подключай при необходимости.</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
