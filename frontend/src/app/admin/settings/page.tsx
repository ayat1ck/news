'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Filter } from 'lucide-react';

interface Setting {
  id: number;
  key: string;
  value: string | null;
  description: string | null;
}

interface FilterRule {
  id: number;
  rule_type: string;
  pattern: string;
  description: string | null;
  is_active: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [rules, setRules] = useState<FilterRule[]>([]);
  const [newRule, setNewRule] = useState({ rule_type: 'blacklist_word', pattern: '', description: '' });
  const [busy, setBusy] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const load = () => {
    apiFetch<Setting[]>('/api/v1/settings/', { token }).then(setSettings).catch(console.error);
    apiFetch<FilterRule[]>('/api/v1/settings/filter-rules', { token }).then(setRules).catch(console.error);
  };

  useEffect(() => {
    load();
  }, []);

  const updateSetting = async (key: string, value: string) => {
    setBusy(key);
    try {
      await apiFetch(`/api/v1/settings/${key}`, { method: 'PUT', body: { value }, token });
      load();
    } finally {
      setBusy('');
    }
  };

  const addRule = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy('new-rule');
    try {
      await apiFetch('/api/v1/settings/filter-rules', { method: 'POST', body: newRule, token });
      setNewRule({ rule_type: 'blacklist_word', pattern: '', description: '' });
      load();
    } finally {
      setBusy('');
    }
  };

  const deleteRule = async (id: number) => {
    setBusy(`rule-${id}`);
    try {
      await apiFetch(`/api/v1/settings/filter-rules/${id}`, { method: 'DELETE', token });
      load();
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="max-w-4xl space-y-10 pb-20">
      <section>
        <h3 className="mb-5 text-lg font-bold">Системные настройки</h3>
        <Card className="divide-y divide-neutral-100">
          {settings.length === 0 ? (
            <div className="p-6 text-sm text-neutral-500">Настройки пока не созданы.</div>
          ) : (
            settings.map((setting) => (
              <div key={setting.id} className="flex items-center justify-between gap-4 p-5">
                <div className="flex-1">
                  <p className="text-sm font-bold">{setting.key}</p>
                  {setting.description && <p className="mt-1 text-xs text-neutral-400">{setting.description}</p>}
                </div>
                <input
                  defaultValue={setting.value || ''}
                  onBlur={(e) => updateSetting(setting.key, e.target.value)}
                  className="w-56 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
                />
              </div>
            ))
          )}
        </Card>
      </section>

      <section>
        <h3 className="mb-5 text-lg font-bold">Фильтры</h3>
        <Card className="divide-y divide-neutral-100">
          {rules.length === 0 ? (
            <div className="p-6 text-sm text-neutral-500">Фильтры пока не настроены.</div>
          ) : (
            rules.map((rule) => (
              <div key={rule.id} className="flex items-center justify-between gap-4 p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-100">
                    <Filter className="h-4 w-4 text-neutral-400" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">{rule.rule_type}: {rule.pattern}</p>
                    {rule.description && <p className="mt-1 text-xs text-neutral-400">{rule.description}</p>}
                  </div>
                </div>
                <Button variant="danger" disabled={Boolean(busy)} onClick={() => deleteRule(rule.id)}>
                  Удалить
                </Button>
              </div>
            ))
          )}
        </Card>

        <form onSubmit={addRule} className="mt-6 flex flex-wrap items-end gap-4 rounded-2xl border border-neutral-100 bg-white p-5">
          <div>
            <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Тип</label>
            <select
              className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              value={newRule.rule_type}
              onChange={(e) => setNewRule({ ...newRule, rule_type: e.target.value })}
            >
              <option value="blacklist_word">Blacklist Word</option>
              <option value="topic_match">Topic Match</option>
              <option value="language_rule">Language Rule</option>
              <option value="source_allow">Source Allow</option>
            </select>
          </div>
          <div className="min-w-[220px] flex-1">
            <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Паттерн</label>
            <input
              className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              value={newRule.pattern}
              onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
              required
            />
          </div>
          <div className="min-w-[220px] flex-1">
            <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Описание</label>
            <input
              className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              value={newRule.description}
              onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
            />
          </div>
          <Button type="submit" disabled={Boolean(busy)}>Добавить фильтр</Button>
        </form>
      </section>
    </div>
  );
}
