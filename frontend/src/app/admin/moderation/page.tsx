'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CheckCircle2, Send } from 'lucide-react';

interface CanonicalItem {
  id: number;
  headline: string | null;
  summary: string | null;
  body: string | null;
  status: string;
  tags: string | null;
  created_at: string;
}

interface ListResponse {
  items: CanonicalItem[];
  total: number;
  page: number;
  page_size: number;
}

export default function ModerationPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [selected, setSelected] = useState<CanonicalItem | null>(null);
  const [editHeadline, setEditHeadline] = useState('');
  const [editSummary, setEditSummary] = useState('');
  const [editBody, setEditBody] = useState('');
  const [busy, setBusy] = useState(false);
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadQueue = () => {
    apiFetch<ListResponse>('/api/v1/moderation/queue?page_size=50', { token }).then((response) => {
      setData(response);
      if (selected) {
        const next = response.items.find((item) => item.id === selected.id) || null;
        setSelected(next);
      }
    }).catch(console.error);
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const selectItem = (item: CanonicalItem) => {
    setSelected(item);
    setEditHeadline(item.headline || '');
    setEditSummary(item.summary || '');
    setEditBody(item.body || '');
  };

  const handleAction = async (action: 'approve' | 'reject') => {
    if (!selected) return;
    setBusy(true);
    try {
      await apiFetch(`/api/v1/moderation/${selected.id}/action`, {
        method: 'POST',
        body: {
          action,
          edits: {
            headline: editHeadline,
            summary: editSummary,
            body: editBody,
          },
        },
        token,
      });
      setSelected(null);
      loadQueue();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <Card className="p-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Queue</p>
            <h3 className="text-lg font-bold">В очереди {data?.total || 0}</h3>
          </div>
        </div>
        <div className="space-y-3">
          {data?.items.length ? data.items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => selectItem(item)}
              className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                selected?.id === item.id ? 'border-black/30 bg-neutral-50' : 'border-neutral-100 hover:border-black/20'
              }`}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <Badge variant="warning">{item.status}</Badge>
                <span className="text-[10px] text-neutral-400">{new Date(item.created_at).toLocaleString('ru-RU')}</span>
              </div>
              <h4 className="line-clamp-2 text-sm font-bold">{item.headline || '(без заголовка)'}</h4>
              <p className="mt-2 line-clamp-2 text-xs text-neutral-500">{item.summary || '—'}</p>
            </button>
          )) : (
            <div className="p-4 text-sm text-neutral-500">Очередь пуста.</div>
          )}
        </div>
      </Card>

      <Card className="p-6">
        {selected ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Исходная версия</p>
              <div className="rounded-2xl bg-neutral-50 p-5">
                <h4 className="text-xl font-bold leading-tight">{selected.headline || '(без заголовка)'}</h4>
                {selected.summary && <p className="mt-4 text-sm text-neutral-600">{selected.summary}</p>}
                <div className="mt-5 whitespace-pre-wrap text-sm leading-relaxed text-neutral-700">{selected.body || 'Текст отсутствует.'}</div>
              </div>
            </div>

            <div className="space-y-4">
              <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Редактура</p>
              <div className="space-y-4">
                <input
                  value={editHeadline}
                  onChange={(e) => setEditHeadline(e.target.value)}
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-lg font-bold outline-none focus:border-black/30"
                  placeholder="Заголовок"
                />
                <textarea
                  value={editSummary}
                  onChange={(e) => setEditSummary(e.target.value)}
                  className="h-28 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm outline-none focus:border-black/30"
                  placeholder="Краткое summary"
                />
                <textarea
                  value={editBody}
                  onChange={(e) => setEditBody(e.target.value)}
                  className="h-72 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm leading-relaxed outline-none focus:border-black/30"
                  placeholder="Текст публикации"
                />
              </div>
              <div className="flex flex-wrap gap-3 border-t border-neutral-100 pt-5">
                <Button disabled={busy} onClick={() => handleAction('approve')}>
                  <CheckCircle2 className="w-4 h-4" /> Approve
                </Button>
                <Button variant="secondary" disabled={busy} onClick={() => handleAction('reject')}>
                  Reject
                </Button>
                <Button variant="outline" disabled>
                  <Send className="w-4 h-4" /> Publish after approval
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-neutral-500">Выбери материал из очереди, чтобы отредактировать и утвердить его.</div>
        )}
      </Card>
    </div>
  );
}
