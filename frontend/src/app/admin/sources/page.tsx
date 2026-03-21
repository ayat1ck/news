'use client';

import { useEffect, useState } from 'react';
import { Plus, Search } from 'lucide-react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';

interface Source {
  id: number;
  source_type: string;
  name: string;
  channel_username: string | null;
  feed_url: string | null;
  vk_domain: string | null;
  language: string;
  topic: string | null;
  priority: number;
  is_active: boolean;
  last_collected_at: string | null;
  latest_raw_at: string | null;
  total_items: number;
  recent_items_24h: number;
  health_status: string;
}

const EMPTY_FORM = {
  source_type: 'rss',
  name: '',
  feed_url: '',
  channel_username: '',
  vk_domain: '',
  language: 'ru',
  topic: 'industry',
  priority: 5,
};

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString('ru-RU') : '—';
}

function getHealthLabel(status: string) {
  if (status === 'healthy') return 'Работает';
  if (status === 'stale') return 'Устарел';
  if (status === 'blocked') return 'Проблема';
  if (status === 'empty') return 'Пусто';
  if (status === 'inactive') return 'Выключен';
  return 'Неизвестно';
}

function getHealthTone(status: string) {
  if (status === 'healthy') return 'bg-green-100 text-green-700';
  if (status === 'stale') return 'bg-amber-100 text-amber-700';
  if (status === 'blocked') return 'bg-red-100 text-red-700';
  if (status === 'empty') return 'bg-blue-100 text-blue-700';
  return 'bg-neutral-100 text-neutral-500';
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadSources = () => {
    apiFetch<Source[]>('/api/v1/sources/', { token })
      .then((response) => {
        setSources(response);
        setError('');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить источники'));
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await apiFetch('/api/v1/sources/', {
        method: 'POST',
        body: form,
        token,
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      loadSources();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать источник');
    }
  };

  const toggleActive = async (source: Source) => {
    await apiFetch(`/api/v1/sources/${source.id}`, {
      method: 'PUT',
      body: { is_active: !source.is_active },
      token,
    });
    loadSources();
  };

  const filteredSources = sources.filter((source) => {
    const haystack = [
      source.name,
      source.feed_url,
      source.channel_username,
      source.vk_domain,
      source.topic,
      source.source_type,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return haystack.includes(search.toLowerCase());
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Поиск источников..."
            className="w-full rounded-xl border border-neutral-200 py-2 pl-9 pr-4 text-sm outline-none focus:ring-1 focus:ring-black"
          />
        </div>
        <Button className="w-full sm:w-auto" onClick={() => setShowForm((value) => !value)}>
          <Plus className="h-4 w-4" />
          {showForm ? 'Закрыть форму' : 'Добавить источник'}
        </Button>
      </div>

      {showForm && (
        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Тип</label>
                <select
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.source_type}
                  onChange={(event) => setForm({ ...form, source_type: event.target.value })}
                >
                  <option value="rss">RSS / Сайт</option>
                  <option value="telegram">Telegram</option>
                  <option value="vk">VK</option>
                </select>
              </div>
              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Название</label>
                <input
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  required
                />
              </div>

              {form.source_type === 'rss' && (
                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">RSS feed или URL сайта</label>
                  <input
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                    value={form.feed_url}
                    onChange={(event) => setForm({ ...form, feed_url: event.target.value })}
                    placeholder="https://example.com/feed.xml или https://example.com/news"
                  />
                </div>
              )}

              {form.source_type === 'telegram' && (
                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Username канала</label>
                  <input
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                    value={form.channel_username}
                    onChange={(event) => setForm({ ...form, channel_username: event.target.value })}
                    placeholder="@channel_name"
                  />
                </div>
              )}

              {form.source_type === 'vk' && (
                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">VK domain</label>
                  <input
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                    value={form.vk_domain}
                    onChange={(event) => setForm({ ...form, vk_domain: event.target.value })}
                    placeholder="public_name"
                  />
                </div>
              )}

              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Язык</label>
                <input
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.language}
                  onChange={(event) => setForm({ ...form, language: event.target.value })}
                />
              </div>
              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Тематика</label>
                <input
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.topic}
                  onChange={(event) => setForm({ ...form, topic: event.target.value })}
                />
              </div>
              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Приоритет (0-10)</label>
                <input
                  type="number"
                  min={0}
                  max={10}
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.priority}
                  onChange={(event) => setForm({ ...form, priority: Number(event.target.value) })}
                />
              </div>
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit">Создать источник</Button>
          </form>
        </Card>
      )}

      {error && !showForm && <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <Card className="overflow-x-auto border-none shadow-none">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-neutral-100 bg-neutral-50 text-neutral-500">
            <tr>
              <th className="px-6 py-4">Название</th>
              <th className="px-6 py-4">Тип</th>
              <th className="px-6 py-4">Тематика</th>
              <th className="px-6 py-4">Состояние</th>
              <th className="px-6 py-4">Сбор</th>
              <th className="px-6 py-4">Статус</th>
              <th className="px-6 py-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-50">
            {filteredSources.map((source) => (
              <tr key={source.id} className="transition-colors hover:bg-neutral-50/50">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-bold">{source.name}</p>
                    <p className="mt-1 text-xs text-neutral-400">
                      {source.feed_url || source.channel_username || source.vk_domain || '—'}
                    </p>
                  </div>
                </td>
                <td className="px-6 py-4 text-[10px] uppercase text-neutral-500">{source.source_type}</td>
                <td className="px-6 py-4"><Badge>{source.topic || '—'}</Badge></td>
                <td className="px-6 py-4">
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold ${getHealthTone(source.health_status)}`}>
                    {getHealthLabel(source.health_status)}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs text-neutral-500">
                  <div>{source.total_items} всего</div>
                  <div>{source.recent_items_24h} за 24ч</div>
                  <div>Последний raw: {formatDate(source.latest_raw_at)}</div>
                  <div>Последний сбор: {formatDate(source.last_collected_at)}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium">{source.language}</div>
                  <div className="mt-1 text-xs text-neutral-500">Приоритет {source.priority}</div>
                  <div className="mt-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${source.is_active ? 'bg-green-100 text-green-700' : 'bg-neutral-100 text-neutral-500'}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${source.is_active ? 'bg-green-500' : 'bg-neutral-400'}`} />
                      {source.is_active ? 'Активен' : 'Отключен'}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <Button variant="ghost" className="h-auto p-2" onClick={() => toggleActive(source)}>
                    {source.is_active ? 'Отключить' : 'Включить'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
