'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, Globe, ImagePlus, Loader2, RefreshCw, Send, Sparkles, Trash2 } from 'lucide-react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';

interface CanonicalItem {
  id: number;
  headline: string | null;
  summary: string | null;
  body: string | null;
  status: string;
  tags: string | null;
  topics: string | null;
  ai_provider: string | null;
  ai_model: string | null;
  media_url: string | null;
  source_url: string | null;
  created_at: string;
  published_at: string | null;
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
  const [busyAction, setBusyAction] = useState('');
  const [feedback, setFeedback] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadItems = () => {
    const params = new URLSearchParams({ page_size: '50' });
    if (status) params.set('status_filter', status);
    apiFetch<ListResponse>(`/api/v1/canonical-items/?${params.toString()}`, { token })
      .then((response) => {
        setData(response);
        if (selected) {
          setSelected(response.items.find((item) => item.id === selected.id) || null);
        }
      })
      .catch(console.error);
  };

  useEffect(() => {
    loadItems();
  }, [status]);

  const refreshSelected = async (id: number) => {
    const fresh = await apiFetch<CanonicalItem>(`/api/v1/canonical-items/${id}`, { token });
    setSelected(fresh);
  };

  const runAction = async (key: string, fn: () => Promise<void>, successMessage: string) => {
    setBusyAction(key);
    setFeedback('');
    try {
      await fn();
      setFeedback(successMessage);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Операция завершилась с ошибкой');
    } finally {
      setBusyAction('');
    }
  };

  const moderate = async (id: number, action: 'approve' | 'reject') => {
    await runAction(
      action,
      async () => {
        await apiFetch(`/api/v1/moderation/${id}/action`, { method: 'POST', body: { action }, token });
        await refreshSelected(id);
        loadItems();
      },
      action === 'approve' ? 'Статья одобрена.' : 'Статья отклонена.',
    );
  };

  const rewrite = async (id: number) => {
    await runAction(
      'rewrite',
      async () => {
        await apiFetch(`/api/v1/moderation/${id}/rewrite`, {
          method: 'POST',
          body: { preserve_headline: false },
          token,
        });
        await refreshSelected(id);
        loadItems();
      },
      'ИИ-рерайт завершен.',
    );
  };

  const generatePreview = async (id: number, regenerate = false) => {
    await runAction(
      regenerate ? 'regenerate-image' : 'generate-image',
      async () => {
        await apiFetch(`/api/v1/moderation/${id}/preview-image`, {
          method: 'POST',
          body: { regenerate, safe_mode: regenerate },
          token,
        });
        await refreshSelected(id);
        loadItems();
      },
      regenerate ? 'Превью перегенерировано.' : 'Превью сгенерировано.',
    );
  };

  const publish = async (id: number, targets: string[]) => {
    const item = data?.items.find((entry) => entry.id === id) || selected;
    const label = item?.headline || `#${id}`;
    const confirmed = window.confirm(`Опубликовать "${label}" в ${targets.join(' + ')}?`);
    if (!confirmed) return;

    await runAction(
      `publish-${targets.join('-')}`,
      async () => {
        await apiFetch(`/api/v1/publishing/${id}/publish`, { method: 'POST', body: { targets }, token });
        setSelected((current) => (current && current.id === id ? { ...current, status: 'published' } : current));
        loadItems();
      },
      `Задача публикации отправлена: ${targets.join(', ')}.`,
    );
  };

  const deleteItem = async (item: CanonicalItem) => {
    const confirmed = window.confirm(`Удалить каноничную статью "${item.headline || `#${item.id}`}"?`);
    if (!confirmed) return;
    await runAction(
      'delete',
      async () => {
        await apiFetch(`/api/v1/canonical-items/${item.id}`, { method: 'DELETE', token });
        setSelected(null);
        loadItems();
      },
      'Статья удалена.',
    );
  };

  const variant = (value: string) =>
    value === 'published' ? 'success' : value === 'pending_review' ? 'warning' : value === 'approved' ? 'default' : 'default';

  const renderBusyIcon = (key: string) =>
    busyAction === key ? <Loader2 className="h-4 w-4 animate-spin" /> : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 rounded-lg bg-neutral-100 p-1 w-fit">
        {[
          ['', 'Все'],
          ['pending_review', 'На модерации'],
          ['approved', 'Одобрено'],
          ['published', 'Опубликовано'],
          ['rejected', 'Отклонено'],
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

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_30rem]">
        <div className="space-y-4">
          {data?.items.length ? (
            data.items.map((item) => (
              <Card key={item.id} className={`cursor-pointer p-5 ${selected?.id === item.id ? 'border-black/30' : ''}`}>
                <button type="button" className="w-full text-left" onClick={() => setSelected(item)}>
                  <div className="mb-3 flex items-center justify-between gap-4">
                    <Badge variant={variant(item.status) as 'default' | 'success' | 'warning'}>{item.status}</Badge>
                    <span className="text-xs text-neutral-400">{new Date(item.created_at).toLocaleString('ru-RU')}</span>
                  </div>
                  <h4 className="text-lg font-bold leading-tight">{item.headline || '(без заголовка)'}</h4>
                  {item.summary && <p className="mt-3 line-clamp-2 text-sm text-neutral-600">{item.summary}</p>}
                  <div className="mt-4 flex flex-wrap gap-3 text-xs text-neutral-400">
                    <span>ИИ: {item.ai_provider || '—'}</span>
                    {item.topics && <span>Тема: {item.topics}</span>}
                  </div>
                </button>
              </Card>
            ))
          ) : (
            <Card className="p-8 text-center text-neutral-500">Каноничных статей нет.</Card>
          )}
        </div>

        <Card className="p-6">
          {selected ? (
            <div className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Каноничная статья #{selected.id}</p>
                  <h3 className="mt-2 text-2xl font-bold leading-tight">{selected.headline || '(без заголовка)'}</h3>
                </div>
                {busyAction && (
                  <span className="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Выполняется: {busyAction}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={variant(selected.status) as 'default' | 'success' | 'warning'}>{selected.status}</Badge>
                <Badge variant="default">ИИ: {selected.ai_provider || '—'}</Badge>
                {selected.topics && <Badge variant="default">{selected.topics}</Badge>}
                {selected.slug && <Badge variant="default">{selected.slug}</Badge>}
              </div>
              {selected.media_url ? (
                <div className="relative overflow-hidden rounded-2xl border border-neutral-100">
                  {busyAction.includes('image') && <div className="absolute inset-0 z-10 animate-pulse bg-white/50" />}
                  <img
                    src={selected.media_url}
                    alt={selected.headline || 'превью'}
                    className="h-48 w-full object-cover"
                  />
                </div>
              ) : (
                <div className="flex h-48 items-center justify-center rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 text-sm text-neutral-400">
                  {busyAction.includes('image') ? 'Генерация превью...' : 'Превью-изображение отсутствует'}
                </div>
              )}
              {selected.summary && (
                <div className="rounded-2xl border border-neutral-100 bg-neutral-50 p-4 text-sm leading-relaxed text-neutral-700">
                  {selected.summary}
                </div>
              )}
              <div className="max-h-[24rem] overflow-y-auto whitespace-pre-wrap rounded-2xl bg-white text-sm leading-relaxed text-neutral-700">
                {selected.body || 'Текст статьи отсутствует.'}
              </div>
              {feedback && (
                <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-700">
                  {feedback}
                </div>
              )}
              <div className="flex flex-wrap gap-3 border-t border-neutral-100 pt-5">
                <Button variant="outline" disabled={Boolean(busyAction)} onClick={() => rewrite(selected.id)}>
                  {renderBusyIcon('rewrite')}
                  <Sparkles className="w-4 h-4" /> ИИ-рерайт
                </Button>
                <Button variant="outline" disabled={Boolean(busyAction)} onClick={() => generatePreview(selected.id, false)}>
                  {renderBusyIcon('generate-image')}
                  <ImagePlus className="w-4 h-4" /> Сгенерировать превью
                </Button>
                <Button variant="outline" disabled={Boolean(busyAction)} onClick={() => generatePreview(selected.id, true)}>
                  {renderBusyIcon('regenerate-image')}
                  <RefreshCw className="w-4 h-4" /> Перегенерировать превью
                </Button>
                {selected.status === 'pending_review' && (
                  <>
                    <Button disabled={Boolean(busyAction)} onClick={() => moderate(selected.id, 'approve')}>
                      {renderBusyIcon('approve')}
                      <CheckCircle2 className="w-4 h-4" /> Одобрить
                    </Button>
                    <Button variant="secondary" disabled={Boolean(busyAction)} onClick={() => moderate(selected.id, 'reject')}>
                      {renderBusyIcon('reject')}
                      Отклонить
                    </Button>
                  </>
                )}
                {(selected.status === 'approved' || selected.status === 'scheduled') && (
                  <>
                    <Button disabled={Boolean(busyAction)} onClick={() => publish(selected.id, ['website'])}>
                      {renderBusyIcon('publish-website')}
                      <Globe className="w-4 h-4" /> Опубликовать на сайт
                    </Button>
                    <Button variant="secondary" disabled={Boolean(busyAction)} onClick={() => publish(selected.id, ['telegram'])}>
                      {renderBusyIcon('publish-telegram')}
                      <Send className="w-4 h-4" /> Опубликовать в Telegram
                    </Button>
                    <Button variant="outline" disabled={Boolean(busyAction)} onClick={() => publish(selected.id, ['website', 'telegram'])}>
                      {renderBusyIcon('publish-website-telegram')}
                      Опубликовать везде
                    </Button>
                  </>
                )}
                {selected.status === 'published' && selected.slug && (
                  <a href={`/article/${selected.slug}`} target="_blank" rel="noreferrer">
                    <Button variant="outline">
                      <Globe className="w-4 h-4" /> Открыть статью
                    </Button>
                  </a>
                )}
                <Button variant="secondary" disabled={Boolean(busyAction)} onClick={() => deleteItem(selected)}>
                  {renderBusyIcon('delete')}
                  <Trash2 className="w-4 h-4" /> Удалить
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-neutral-500">Выбери каноничную статью, чтобы посмотреть, отредактировать, сгенерировать превью или опубликовать ее.</div>
          )}
        </Card>
      </div>
    </div>
  );
}
