'use client';

import { useEffect, useState } from 'react';
import { Filter } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';

interface FilterRule {
  id: number;
  rule_type: string;
  pattern: string;
  description: string | null;
  is_active: boolean;
}

function ruleTypeLabel(value: string) {
  if (value === 'blacklist_word') return 'Стоп-слово';
  if (value === 'topic_match') return 'Сопоставление темы';
  if (value === 'language_rule') return 'Правило языка';
  if (value === 'source_allow') return 'Разрешенный источник';
  return value;
}

export default function SettingsPage() {
  const [rules, setRules] = useState<FilterRule[]>([]);
  const [newRule, setNewRule] = useState({
    rule_type: 'blacklist_word',
    pattern: '',
    description: '',
  });
  const [busy, setBusy] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const load = () => {
    apiFetch<FilterRule[]>('/api/v1/settings/filter-rules', { token })
      .then(setRules)
      .catch(console.error);
  };

  useEffect(() => {
    load();
  }, []);

  const addRule = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy('new-rule');
    try {
      await apiFetch('/api/v1/settings/filter-rules', {
        method: 'POST',
        body: newRule,
        token,
      });
      setNewRule({ rule_type: 'blacklist_word', pattern: '', description: '' });
      load();
    } finally {
      setBusy('');
    }
  };

  const deleteRule = async (id: number) => {
    setBusy(`rule-${id}`);
    try {
      await apiFetch(`/api/v1/settings/filter-rules/${id}`, {
        method: 'DELETE',
        token,
      });
      load();
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="max-w-4xl space-y-8 pb-20">
      <section>
        <div className="mb-5">
          <h3 className="text-lg font-bold">Правила фильтрации</h3>
          <p className="mt-1 text-sm text-neutral-500">
            Здесь оставлены только реально работающие правила фильтрации. Фальшивые runtime-настройки убраны.
          </p>
        </div>

        <Card className="divide-y divide-neutral-100">
          {rules.length === 0 ? (
            <div className="p-6 text-sm text-neutral-500">Правила фильтрации пока не настроены.</div>
          ) : (
            rules.map((rule) => (
              <div key={rule.id} className="flex items-center justify-between gap-4 p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-100">
                    <Filter className="h-4 w-4 text-neutral-400" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">{ruleTypeLabel(rule.rule_type)}: {rule.pattern}</p>
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
              onChange={(event) => setNewRule({ ...newRule, rule_type: event.target.value })}
            >
              <option value="blacklist_word">Стоп-слово</option>
              <option value="topic_match">Сопоставление темы</option>
              <option value="language_rule">Правило языка</option>
              <option value="source_allow">Разрешенный источник</option>
            </select>
          </div>

          <div className="min-w-[220px] flex-1">
            <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Паттерн</label>
            <input
              className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              value={newRule.pattern}
              onChange={(event) => setNewRule({ ...newRule, pattern: event.target.value })}
              required
            />
          </div>

          <div className="min-w-[220px] flex-1">
            <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Описание</label>
            <input
              className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              value={newRule.description}
              onChange={(event) => setNewRule({ ...newRule, description: event.target.value })}
            />
          </div>

          <Button type="submit" disabled={Boolean(busy)}>Добавить правило</Button>
        </form>
      </section>
    </div>
  );
}
