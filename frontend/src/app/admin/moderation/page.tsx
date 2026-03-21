'use client';

import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ImagePlus, Loader2, RefreshCw, Send, Sparkles, Trash2 } from 'lucide-react';

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
  image_prompt: string | null;
  media_url: string | null;
  source_url: string | null;
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
  const [busyAction, setBusyAction] = useState('');
  const [feedback, setFeedback] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadQueue = () => {
    apiFetch<ListResponse>('/api/v1/moderation/queue?page_size=50', { token })
      .then((response) => {
        setData(response);
        if (selected) {
          const next = response.items.find((item) => item.id === selected.id) || null;
          if (next) {
            setSelected(next);
          }
        }
      })
      .catch(console.error);
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const selectItem = (item: CanonicalItem) => {
    setSelected(item);
    setEditHeadline(item.headline || '');
    setEditSummary(item.summary || '');
    setEditBody(item.body || '');
    setFeedback('');
  };

  const refreshSelected = async (id: number) => {
    const fresh = await apiFetch<CanonicalItem>(`/api/v1/canonical-items/${id}`, { token });
    setSelected(fresh);
    setEditHeadline(fresh.headline || '');
    setEditSummary(fresh.summary || '');
    setEditBody(fresh.body || '');
  };

  const preview = useMemo(() => {
    if (!selected) return null;
    return {
      ...selected,
      headline: editHeadline || selected.headline,
      summary: editSummary || selected.summary,
      body: editBody || selected.body,
    };
  }, [selected, editHeadline, editSummary, editBody]);

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

  const handleAction = async (action: 'approve' | 'reject') => {
    if (!selected) return;
    await runAction(
      action,
      async () => {
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

        if (action === 'approve' || action === 'reject') {
          setSelected(null);
        }
        loadQueue();
      },
      action === 'approve' ? 'Статья одобрена.' : 'Статья отклонена.',
    );
  };

  const handleRewrite = async () => {
    if (!selected) return;
    await runAction(
      'rewrite',
      async () => {
        await apiFetch(`/api/v1/moderation/${selected.id}/rewrite`, {
          method: 'POST',
          body: { preserve_headline: false },
          token,
        });
        await refreshSelected(selected.id);
        loadQueue();
      },
      'ИИ-рерайт завершен.',
    );
  };

  const handlePreviewImage = async (regenerate = false) => {
    if (!selected) return;
    await runAction(
      regenerate ? 'regenerate-image' : 'generate-image',
      async () => {
        await apiFetch(`/api/v1/moderation/${selected.id}/preview-image`, {
          method: 'POST',
          body: { regenerate, safe_mode: regenerate },
          token,
        });
        await refreshSelected(selected.id);
        loadQueue();
      },
      regenerate ? 'Превью перегенерировано.' : 'Превью сгенерировано.',
    );
  };

  const handleDelete = async () => {
    if (!selected) return;
    const confirmed = window.confirm(`Удалить каноничную статью "${selected.headline || `#${selected.id}`}"?`);
    if (!confirmed) return;
    await runAction(
      'delete',
      async () => {
        await apiFetch(`/api/v1/canonical-items/${selected.id}`, { method: 'DELETE', token });
        setSelected(null);
        loadQueue();
      },
      'Статья удалена.',
    );
  };

  const renderBusyIcon = (key: string) =>
    busyAction === key ? <Loader2 className="h-4 w-4 animate-spin" /> : null;

  return (
    <div className="grid gap-6 xl:grid-cols-[24rem_minmax(0,1fr)]">
      <Card className="p-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Очередь</p>
            <h3 className="text-lg font-bold">Ожидают модерации: {data?.total || 0}</h3>
          </div>
        </div>
        <div className="space-y-3">
          {data?.items.length ? (
            data.items.map((item) => (
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
            ))
          ) : (
            <div className="p-4 text-sm text-neutral-500">Очередь пуста.</div>
          )}
        </div>
      </Card>

      <Card className="p-6">
        {selected && preview ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Live preview</p>
                {busyAction && (
                  <span className="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Выполняется: {busyAction}
                  </span>
                )}
              </div>
              <div className="rounded-2xl bg-neutral-50 p-5 transition-all duration-200">
                <h4 className="text-xl font-bold leading-tight">{preview.headline || '(без заголовка)'}</h4>
                {preview.summary && <p className="mt-4 text-sm text-neutral-600">{preview.summary}</p>}
                <div className="mt-5 whitespace-pre-wrap text-sm leading-relaxed text-neutral-700">{preview.body || 'Текста пока нет.'}</div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-neutral-500">
                  <span>ИИ: {selected.ai_provider || '—'}</span>
                  {selected.ai_model && <span>{selected.ai_model}</span>}
                  {selected.topics && <span>Тема: {selected.topics}</span>}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Редактор</p>
              {selected.media_url ? (
                <div className="relative overflow-hidden rounded-2xl border border-neutral-100">
                  {busyAction.includes('image') && <div className="absolute inset-0 z-10 animate-pulse bg-white/50" />}
                  <img
                    src={selected.media_url}
                    alt={preview.headline || 'превью'}
                    className="h-48 w-full object-cover transition-opacity duration-200"
                  />
                </div>
              ) : (
                <div className="flex h-48 w-full items-center justify-center rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 text-sm text-neutral-400">
                  {busyAction.includes('image') ? 'Генерация превью...' : 'Превью-изображение отсутствует'}
                </div>
              )}
              <div className="space-y-4">
                <input
                  value={editHeadline}
                  onChange={(event) => setEditHeadline(event.target.value)}
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-lg font-bold outline-none focus:border-black/30"
                  placeholder="Заголовок"
                />
                <textarea
                  value={editSummary}
                  onChange={(event) => setEditSummary(event.target.value)}
                  className="h-28 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm outline-none focus:border-black/30"
                  placeholder="Краткое описание"
                />
                <textarea
                  value={editBody}
                  onChange={(event) => setEditBody(event.target.value)}
                  className="h-72 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm leading-relaxed outline-none focus:border-black/30"
                  placeholder="Текст статьи"
                />
              </div>
              {feedback && (
                <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-700">
                  {feedback}
                </div>
              )}
              <div className="flex flex-wrap gap-3 border-t border-neutral-100 pt-5">
                <Button variant="outline" disabled={Boolean(busyAction)} onClick={handleRewrite}>
                  {renderBusyIcon('rewrite')}
                  <Sparkles className="w-4 h-4" /> ИИ-рерайт
                </Button>
                <Button variant="outline" disabled={Boolean(busyAction)} onClick={() => handlePreviewImage(false)}>
                  {renderBusyIcon('generate-image')}
                  <ImagePlus className="w-4 h-4" /> Сгенерировать превью
                </Button>
                <Button variant="outline" disabled={Boolean(busyAction)} onClick={() => handlePreviewImage(true)}>
                  {renderBusyIcon('regenerate-image')}
                  <RefreshCw className="w-4 h-4" /> Перегенерировать превью
                </Button>
                <Button disabled={Boolean(busyAction)} onClick={() => handleAction('approve')}>
                  {renderBusyIcon('approve')}
                  <CheckCircle2 className="w-4 h-4" /> Одобрить
                </Button>
                <Button variant="secondary" disabled={Boolean(busyAction)} onClick={() => handleAction('reject')}>
                  {renderBusyIcon('reject')}
                  Отклонить
                </Button>
                <Button variant="secondary" disabled={Boolean(busyAction)} onClick={handleDelete}>
                  {renderBusyIcon('delete')}
                  <Trash2 className="w-4 h-4" /> Удалить
                </Button>
                <Button variant="outline" disabled>
                  <Send className="w-4 h-4" /> Публикация после одобрения
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-neutral-500">Выбери статью из очереди, чтобы проверить, переписать или одобрить ее.</div>
        )}
      </Card>
    </div>
  );
}
