'use client';

import { useEffect, useState } from 'react';
import { Globe, RefreshCw, Send } from 'lucide-react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';

interface PublishRecord {
  id: number;
  canonical_item_id: number;
  target: string;
  status: string;
  slug: string | null;
  telegram_message_id: number | null;
  telegram_channel_id: string | null;
  error_message: string | null;
  published_at: string | null;
  created_at: string;
}

function targetLabel(value: string) {
  if (value === 'website') return 'Сайт';
  if (value === 'telegram') return 'Telegram';
  return value;
}

export default function PublishingPage() {
  const [records, setRecords] = useState<PublishRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadHistory = () => {
    setLoading(true);
    apiFetch<PublishRecord[]>('/api/v1/publishing/history?page_size=100', { token })
      .then(setRecords)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const variant = (status: string) =>
    status === 'published' ? 'success' : status === 'failed' ? 'danger' : 'warning';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Публикация</p>
          <h3 className="text-2xl font-bold">История публикаций</h3>
        </div>
        <Button variant="outline" onClick={loadHistory}>
          <RefreshCw className="w-4 h-4" /> Обновить
        </Button>
      </div>

      <div className="grid gap-4">
        {loading ? (
          <Card className="p-8 text-center text-neutral-500">Загрузка...</Card>
        ) : records.length === 0 ? (
          <Card className="p-8 text-center text-neutral-500">История публикаций пуста.</Card>
        ) : (
          records.map((record) => (
            <Card key={record.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {record.target === 'website' ? (
                      <Globe className="h-4 w-4 text-neutral-400" />
                    ) : (
                      <Send className="h-4 w-4 text-neutral-400" />
                    )}
                    <span className="text-sm font-bold">#{record.canonical_item_id}</span>
                    <Badge variant={variant(record.status) as 'success' | 'warning' | 'danger'}>{record.status}</Badge>
                    <Badge variant="default">{targetLabel(record.target)}</Badge>
                  </div>
                  <div className="text-sm text-neutral-600">
                    <p>Создано: {new Date(record.created_at).toLocaleString('ru-RU')}</p>
                    {record.published_at && <p>Опубликовано: {new Date(record.published_at).toLocaleString('ru-RU')}</p>}
                    {record.slug && <p>Slug: {record.slug}</p>}
                    {record.telegram_message_id && <p>Сообщение Telegram: {record.telegram_message_id}</p>}
                    {record.telegram_channel_id && <p>Канал: {record.telegram_channel_id}</p>}
                  </div>
                </div>
                {record.error_message ? (
                  <div className="max-w-xl rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {record.error_message}
                  </div>
                ) : null}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
