'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Send, Globe, CheckCircle2 } from 'lucide-react';

interface CanonicalItem {
  id: number;
  headline: string | null;
  summary: string | null;
  body: string | null;
  status: string;
  tags: string | null;
  created_at: string;
  published_at: string | null;
  ai_provider: string | null;
  slug: string | null;
}

interface ListResponse {
  items: CanonicalItem[];
  total: number;
  page: number;
  page_size: number;
}

export default function CanonicalPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [selected, setSelected] = useState<CanonicalItem | null>(null);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadItems = () => {
    const params = new URLSearchParams({ page_size: '50' });
    if (status) params.set('status_filter', status);
    apiFetch<ListResponse>(`/api/v1/canonical-items/?${params}`, { token }).then((response) => {
      setData(response);
      if (selected) {
        setSelected(response.items.find((item) => item.id === selected.id) || null);
      }
    }).catch(console.error);
  };

  useEffect(() => {
    loadItems();
  }, [status]);

  const moderate = async (id: number, action: 'approve' | 'reject') => {
    setBusy(`${action}-${id}`);
    try {
      await apiFetch(`/api/v1/moderation/${id}/action`, { method: 'POST', body: { action }, token });
      loadItems();
    } finally {
      setBusy('');
    }
  };

  const publish = async (id: number, targets: string[]) => {
    const item = data?.items.find((entry) => entry.id === id) || selected;
    const label = item?.headline || `Canonical #${id}`;
    const confirmed = window.confirm(`Publish "${label}" to ${targets.join(' + ')}?`);
    if (!confirmed) return;

    setBusy(`publish-${id}-${targets.join('-')}`);
    try {
      await apiFetch(`/api/v1/publishing/${id}/publish`, { method: 'POST', body: { targets }, token });
      loadItems();
    } finally {
      setBusy('');
    }
  };

  const variant = (value: string) =>
    value === 'published' ? 'success' : value === 'pending_review' ? 'warning' : value === 'approved' ? 'default' : 'default';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 rounded-lg bg-neutral-100 p-1 w-fit">
        {[
          ['', 'Все'],
          ['pending_review', 'Pending'],
          ['approved', 'Approved'],
          ['published', 'Published'],
          ['rejected', 'Rejected'],
        ].map(([value, label]) => (
          <button
            key={value || 'all'}
            type="button"
            onClick={() => setStatus(value)}
            className={`rounded-md px-4 py-1.5 text-xs font-bold transition-colors ${
              status === value ? 'bg-white shadow-sm text-black' : 'text-neutral-500 hover:text-black'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_28rem]">
        <div className="space-y-4">
          {data?.items.length ? data.items.map((item) => (
            <Card
              key={item.id}
              className={`cursor-pointer p-5 ${selected?.id === item.id ? 'border-black/30' : ''}`}
            >
              <button type="button" className="w-full text-left" onClick={() => setSelected(item)}>
                <div className="mb-3 flex items-center justify-between gap-4">
                  <Badge variant={variant(item.status) as 'default' | 'success' | 'warning'}>{item.status}</Badge>
                  <span className="text-xs text-neutral-400">{new Date(item.created_at).toLocaleString('ru-RU')}</span>
                </div>
                <h4 className="text-lg font-bold leading-tight">{item.headline || '(без заголовка)'}</h4>
                {item.summary && <p className="mt-3 line-clamp-2 text-sm text-neutral-600">{item.summary}</p>}
                <div className="mt-4 flex flex-wrap gap-3 text-xs text-neutral-400">
                  <span>AI: {item.ai_provider || '—'}</span>
                  {item.tags && <span>Теги: {item.tags}</span>}
                </div>
              </button>
            </Card>
          )) : (
            <Card className="p-8 text-center text-neutral-500">Нет canonical-статей</Card>
          )}
        </div>

        <Card className="p-6">
          {selected ? (
            <div className="space-y-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Canonical #{selected.id}</p>
                <h3 className="mt-2 text-2xl font-bold leading-tight">{selected.headline || '(без заголовка)'}</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={variant(selected.status) as 'default' | 'success' | 'warning'}>{selected.status}</Badge>
                <Badge variant="default">ID {selected.id}</Badge>
                {selected.slug && <Badge variant="default">{selected.slug}</Badge>}
              </div>
              {selected.summary && (
                <div className="rounded-2xl border border-neutral-100 bg-neutral-50 p-4 text-sm leading-relaxed text-neutral-700">
                  {selected.summary}
                </div>
              )}
              <div className="max-h-[24rem] overflow-y-auto rounded-2xl bg-white text-sm leading-relaxed text-neutral-700 whitespace-pre-wrap">
                {selected.body || 'Текст статьи отсутствует.'}
              </div>
              <div className="flex flex-wrap gap-3 border-t border-neutral-100 pt-5">
                {selected.status === 'pending_review' && (
                  <>
                    <Button disabled={Boolean(busy)} onClick={() => moderate(selected.id, 'approve')}>
                      <CheckCircle2 className="w-4 h-4" /> Approve
                    </Button>
                    <Button variant="secondary" disabled={Boolean(busy)} onClick={() => moderate(selected.id, 'reject')}>
                      Reject
                    </Button>
                  </>
                )}
                {(selected.status === 'approved' || selected.status === 'scheduled') && (
                  <>
                    <Button disabled={Boolean(busy)} onClick={() => publish(selected.id, ['website'])}>
                      <Globe className="w-4 h-4" /> Publish to website
                    </Button>
                    <Button variant="secondary" disabled={Boolean(busy)} onClick={() => publish(selected.id, ['telegram'])}>
                      <Send className="w-4 h-4" /> Publish to Telegram
                    </Button>
                    <Button variant="outline" disabled={Boolean(busy)} onClick={() => publish(selected.id, ['website', 'telegram'])}>
                      Publish everywhere
                    </Button>
                  </>
                )}
                {selected.status === 'published' && selected.slug && (
                  <a href={`/article/${selected.slug}`} target="_blank" rel="noreferrer">
                    <Button variant="outline"><Globe className="w-4 h-4" /> Open public article</Button>
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-neutral-500">Выбери canonical-статью, чтобы модерировать или публиковать её.</div>
          )}
        </Card>
      </div>
    </div>
  );
}
