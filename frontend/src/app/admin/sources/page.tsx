'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Plus, Search } from 'lucide-react';

interface Source {
  id: number;
  source_type: string;
  name: string;
  channel_username: string | null;
  feed_url: string | null;
  language: string;
  topic: string | null;
  priority: number;
  is_active: boolean;
  last_collected_at: string | null;
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    source_type: 'rss',
    name: '',
    feed_url: '',
    channel_username: '',
    language: 'en',
    topic: 'general',
    priority: 5,
  });

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const loadSources = () => {
    apiFetch<Source[]>('/api/v1/sources/', { token }).then(setSources).catch(console.error);
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await apiFetch('/api/v1/sources/', { method: 'POST', body: form, token });
      setShowForm(false);
      setForm({ source_type: 'rss', name: '', feed_url: '', channel_username: '', language: 'en', topic: 'general', priority: 5 });
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

  const priorityLabel = (priority: number) => (priority >= 8 ? 'Высокий' : priority >= 4 ? 'Средний' : 'Низкий');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <input
            type="text"
            placeholder="Поиск источников..."
            className="w-full rounded-xl border border-neutral-200 py-2 pl-9 pr-4 text-sm outline-none focus:ring-1 focus:ring-black"
          />
        </div>
        <Button className="w-full sm:w-auto" onClick={() => setShowForm(!showForm)}>
          <Plus className="w-4 h-4" /> {showForm ? 'Закрыть форму' : 'Добавить источник'}
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
                  onChange={(e) => setForm({ ...form, source_type: e.target.value })}
                >
                  <option value="rss">RSS / Website</option>
                  <option value="telegram">Telegram</option>
                </select>
              </div>
              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Название</label>
                <input
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>

              {form.source_type === 'rss' ? (
                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">RSS feed или URL сайта</label>
                  <input
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                    value={form.feed_url}
                    onChange={(e) => setForm({ ...form, feed_url: e.target.value })}
                    placeholder="https://example.com/feed.xml или https://example.com/news"
                  />
                  <p className="mt-2 text-xs text-neutral-400">
                    Если RSS нет, вставь URL сайта или раздела. Система попробует найти статьи на странице автоматически.
                  </p>
                </div>
              ) : (
                <div className="md:col-span-2">
                  <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Username канала</label>
                  <input
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                    value={form.channel_username}
                    onChange={(e) => setForm({ ...form, channel_username: e.target.value })}
                    placeholder="@channel_name"
                  />
                </div>
              )}

              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Язык</label>
                <input
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.language}
                  onChange={(e) => setForm({ ...form, language: e.target.value })}
                />
              </div>
              <div>
                <label className="mb-2 block text-xs font-bold uppercase text-neutral-500">Тематика</label>
                <input
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm outline-none focus:ring-1 focus:ring-black"
                  value={form.topic}
                  onChange={(e) => setForm({ ...form, topic: e.target.value })}
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
                  onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
                />
              </div>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit">Создать источник</Button>
          </form>
        </Card>
      )}

      <Card className="overflow-x-auto border-none shadow-none">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-neutral-100 bg-neutral-50 text-neutral-500">
            <tr>
              <th className="px-6 py-4">Название</th>
              <th className="px-6 py-4">Тип</th>
              <th className="px-6 py-4">Тематика</th>
              <th className="px-6 py-4">Приоритет</th>
              <th className="px-6 py-4">Язык</th>
              <th className="px-6 py-4">Статус</th>
              <th className="px-6 py-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-50">
            {sources.map((source) => (
              <tr key={source.id} className="transition-colors hover:bg-neutral-50/50">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-bold">{source.name}</p>
                    <p className="mt-1 text-xs text-neutral-400">
                      {source.feed_url || source.channel_username || '—'}
                    </p>
                  </div>
                </td>
                <td className="px-6 py-4 text-[10px] uppercase text-neutral-500">{source.source_type}</td>
                <td className="px-6 py-4"><Badge>{source.topic || '—'}</Badge></td>
                <td className="px-6 py-4 text-neutral-500">{priorityLabel(source.priority)}</td>
                <td className="px-6 py-4 font-medium">{source.language}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${
                    source.is_active ? 'bg-green-100 text-green-700' : 'bg-neutral-100 text-neutral-500'
                  }`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${source.is_active ? 'bg-green-500' : 'bg-neutral-400'}`} />
                    {source.is_active ? 'Активен' : 'Отключен'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <Button variant="ghost" className="p-2 h-auto" onClick={() => toggleActive(source)}>
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
