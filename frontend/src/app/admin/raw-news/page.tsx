'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Cpu, Database, ExternalLink, RefreshCw } from 'lucide-react';

interface RawItem {
  id: number;
  title: string | null;
  text: string | null;
  status: string;
  source_id: number;
  collected_at: string;
  published_at: string | null;
  url: string | null;
  media_url: string | null;
}

interface ListResponse {
  items: RawItem[];
  total: number;
  page: number;
  page_size: number;
}

const statusVariant: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  new: 'warning',
  processed: 'success',
  rejected: 'danger',
  duplicate: 'default',
};

export default function RawNewsPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState<RawItem | null>(null);
  const [busy, setBusy] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadItems = () => {
    const params = new URLSearchParams({ page: String(page), page_size: '30' });
    if (status) params.set('status_filter', status);
    apiFetch<ListResponse>(`/api/v1/raw-items/?${params}`, { token }).then(setData).catch(console.error);
  };

  useEffect(() => {
    loadItems();
  }, [page, status]);

  const runOperation = async (path: string, key: string) => {
    setBusy(key);
    try {
      await apiFetch(path, { method: 'POST', token });
      window.setTimeout(loadItems, 1200);
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3">
        <Button
          variant="secondary"
          disabled={Boolean(busy)}
          onClick={() => runOperation('/api/v1/operations/collect-rss', 'collect-rss')}
        >
          <RefreshCw className="w-4 h-4" /> Собрать RSS сейчас
        </Button>
        <Button
          variant="outline"
          disabled={Boolean(busy)}
          onClick={() => runOperation('/api/v1/operations/process', 'process')}
        >
          <Cpu className="w-4 h-4" /> Запустить pipeline
        </Button>
      </div>

      <div className="flex gap-2 rounded-lg bg-neutral-100 p-1 w-fit">
        {[
          ['', 'Все'],
          ['new', 'New'],
          ['processed', 'Processed'],
          ['rejected', 'Rejected'],
          ['duplicate', 'Duplicate'],
        ].map(([value, label]) => (
          <button
            key={value || 'all'}
            type="button"
            onClick={() => {
              setStatus(value);
              setPage(1);
            }}
            className={`rounded-md px-4 py-1.5 text-xs font-bold transition-colors ${
              status === value ? 'bg-white shadow-sm text-black' : 'text-neutral-500 hover:text-black'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="space-y-4">
          {data ? (
            <>
              <p className="text-sm text-neutral-500">Показано {data.items.length} из {data.total}</p>
              {data.items.length === 0 ? (
                <Card className="p-8 text-center text-neutral-500">Нет записей</Card>
              ) : (
                data.items.map((item) => (
                  <Card
                    key={item.id}
                    className={`cursor-pointer p-4 transition-colors hover:border-black/20 ${
                      selected?.id === item.id ? 'border-black/30' : ''
                    }`}
                  >
                    <button
                      type="button"
                      className="flex w-full items-center gap-5 text-left"
                      onClick={() => setSelected(item)}
                    >
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-neutral-100 text-neutral-400">
                        <Database className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-neutral-400">
                            Source #{item.source_id}
                          </span>
                          <Badge variant={statusVariant[item.status] || 'default'}>{item.status}</Badge>
                        </div>
                        <h5 className="truncate text-sm font-bold">{item.title || '(no title)'}</h5>
                        <p className="truncate text-xs italic text-neutral-500">{item.text?.slice(0, 120) || '—'}</p>
                      </div>
                      <span className="text-[10px] text-neutral-400">
                        {new Date(item.collected_at).toLocaleString('ru-RU')}
                      </span>
                    </button>
                  </Card>
                ))
              )}
            </>
          ) : (
            <Card className="p-8 text-center text-neutral-500">Загрузка...</Card>
          )}
        </div>

        <Card className="p-6">
          {selected ? (
            <div className="space-y-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Raw item #{selected.id}</p>
                <h4 className="mt-2 text-xl font-bold leading-tight">{selected.title || '(no title)'}</h4>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={statusVariant[selected.status] || 'default'}>{selected.status}</Badge>
                <Badge variant="default">Source #{selected.source_id}</Badge>
              </div>
              <div className="space-y-2 text-sm text-neutral-600">
                <p><span className="font-semibold text-neutral-900">Собрано:</span> {new Date(selected.collected_at).toLocaleString('ru-RU')}</p>
                {selected.published_at && (
                  <p><span className="font-semibold text-neutral-900">Дата у источника:</span> {new Date(selected.published_at).toLocaleString('ru-RU')}</p>
                )}
                {selected.media_url && <p className="truncate"><span className="font-semibold text-neutral-900">Фото:</span> {selected.media_url}</p>}
              </div>
              <div className="rounded-2xl bg-neutral-50 p-4 text-sm leading-relaxed text-neutral-700 whitespace-pre-wrap">
                {selected.text || 'Текст отсутствует.'}
              </div>
              <div className="flex flex-wrap gap-3">
                {selected.url && (
                  <a href={selected.url} target="_blank" rel="noreferrer">
                    <Button variant="outline"><ExternalLink className="w-4 h-4" /> Открыть источник</Button>
                  </a>
                )}
                {selected.url && (
                  <Button
                    variant="secondary"
                    disabled={Boolean(busy)}
                    onClick={() => runOperation(`/api/v1/raw-items/${selected.id}/fetch-content`, `fetch-${selected.id}`)}
                  >
                    <RefreshCw className="w-4 h-4" /> Добрать полный текст
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-neutral-500">Выбери запись, чтобы посмотреть детали и действия.</div>
          )}
        </Card>
      </div>

      {data && data.total > data.page_size && (
        <div className="flex justify-center gap-4">
          <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Назад
          </Button>
          <span className="py-2 text-sm text-neutral-500">Стр. {page}</span>
          <Button variant="outline" disabled={data.items.length < data.page_size} onClick={() => setPage(page + 1)}>
            Далее
          </Button>
        </div>
      )}
    </div>
  );
}
