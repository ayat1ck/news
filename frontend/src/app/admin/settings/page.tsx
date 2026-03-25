'use client';

import { useEffect, useState } from 'react';
import { Clock3, Filter, KeyRound, MessageCircleMore } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';

interface Setting {
  id: number;
  key: string;
  value: string | null;
  description: string | null;
}

interface TelegramAuthResponse {
  success: boolean;
  message: string;
  session_string: string | null;
}

interface TelegramQrStartResponse {
  success: boolean;
  message: string;
  auth_id: string;
  qr_svg: string;
}

interface TelegramQrStatusResponse {
  success: boolean;
  status: string;
  message: string;
  session_string: string | null;
}

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

function settingValue(settings: Setting[], key: string, fallback = '') {
  return settings.find((item) => item.key === key)?.value || fallback;
}

export default function SettingsPage() {
  const [rules, setRules] = useState<FilterRule[]>([]);
  const [settings, setSettings] = useState<Setting[]>([]);
  const [intervalValue, setIntervalValue] = useState('60');
  const [vkToken, setVkToken] = useState('');
  const [newRule, setNewRule] = useState({
    rule_type: 'blacklist_word',
    pattern: '',
    description: '',
  });
  const [telegramAuth, setTelegramAuth] = useState({
    api_id: '',
    api_hash: '',
    phone: '',
    code: '',
    password: '',
  });
  const [telegramSessionPreview, setTelegramSessionPreview] = useState('');
  const [telegramQr, setTelegramQr] = useState({
    auth_id: '',
    qr_svg: '',
    active: false,
  });
  const [busy, setBusy] = useState('');
  const [feedback, setFeedback] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';

  const load = async () => {
    try {
      const [settingsResponse, rulesResponse] = await Promise.all([
        apiFetch<Setting[]>('/api/v1/settings/', { token }),
        apiFetch<FilterRule[]>('/api/v1/settings/filter-rules', { token }),
      ]);
      setSettings(settingsResponse);
      setRules(rulesResponse);
      setIntervalValue(settingValue(settingsResponse, 'collection_interval_minutes', '60'));
      setVkToken(settingValue(settingsResponse, 'vk_access_token', ''));
      setTelegramAuth((current) => ({
        ...current,
        api_id: settingValue(settingsResponse, 'telegram_api_id', current.api_id),
        api_hash: settingValue(settingsResponse, 'telegram_api_hash', current.api_hash),
      }));
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось загрузить настройки.');
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveInterval = async () => {
    setBusy('interval');
    setFeedback('');
    try {
      await apiFetch('/api/v1/settings/collection_interval_minutes', {
        method: 'PUT',
        body: { value: intervalValue },
        token,
      });
      await load();
      setFeedback('Интервал парсинга сохранен. Новое значение подхватится автоматически.');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось сохранить интервал.');
    } finally {
      setBusy('');
    }
  };

  const saveVkToken = async () => {
    setBusy('vk-token');
    setFeedback('');
    try {
      await apiFetch('/api/v1/settings/vk_access_token', {
        method: 'PUT',
        body: { value: vkToken.trim() },
        token,
      });
      await load();
      setFeedback('VK access token сохранен.');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось сохранить VK token.');
    } finally {
      setBusy('');
    }
  };

  const sendTelegramCode = async () => {
    setBusy('telegram-start');
    setFeedback('');
    setTelegramSessionPreview('');
    try {
      const response = await apiFetch<TelegramAuthResponse>('/api/v1/settings/telegram-auth/start', {
        method: 'POST',
        body: {
          api_id: telegramAuth.api_id,
          api_hash: telegramAuth.api_hash,
          phone: telegramAuth.phone,
        },
        token,
      });
      setFeedback(response.message);
      await load();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось отправить код Telegram.');
    } finally {
      setBusy('');
    }
  };

  const completeTelegramAuth = async () => {
    setBusy('telegram-complete');
    setFeedback('');
    try {
      const response = await apiFetch<TelegramAuthResponse>('/api/v1/settings/telegram-auth/complete', {
        method: 'POST',
        body: {
          code: telegramAuth.code,
          password: telegramAuth.password || undefined,
        },
        token,
      });
      setTelegramSessionPreview(response.session_string || '');
      setFeedback(response.message);
      await load();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось завершить авторизацию Telegram.');
    } finally {
      setBusy('');
    }
  };

  useEffect(() => {
    if (!telegramQr.active || !telegramQr.auth_id) return;

    const interval = window.setInterval(async () => {
      try {
        const response = await apiFetch<TelegramQrStatusResponse>(
          `/api/v1/settings/telegram-auth/qr/status/${telegramQr.auth_id}`,
          { token },
        );
        if (response.status === 'authorized') {
          setTelegramSessionPreview(response.session_string || '');
          setFeedback(response.message);
          setTelegramQr({ auth_id: '', qr_svg: '', active: false });
          await load();
        } else if (response.status === 'password_required') {
          setFeedback(response.message);
          setTelegramQr({ auth_id: '', qr_svg: '', active: false });
        }
      } catch (error) {
        setFeedback(error instanceof Error ? error.message : 'Не удалось проверить статус QR-входа.');
        setTelegramQr({ auth_id: '', qr_svg: '', active: false });
      }
    }, 2000);

    return () => window.clearInterval(interval);
  }, [telegramQr.active, telegramQr.auth_id, token]);

  const startTelegramQrAuth = async () => {
    setBusy('telegram-qr');
    setFeedback('');
    setTelegramSessionPreview('');
    try {
      const response = await apiFetch<TelegramQrStartResponse>('/api/v1/settings/telegram-auth/qr/start', {
        method: 'POST',
        body: {
          api_id: telegramAuth.api_id,
          api_hash: telegramAuth.api_hash,
        },
        token,
      });
      setTelegramQr({
        auth_id: response.auth_id,
        qr_svg: response.qr_svg,
        active: true,
      });
      setFeedback(response.message);
      await load();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось запустить QR-вход Telegram.');
    } finally {
      setBusy('');
    }
  };

  const addRule = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy('new-rule');
    setFeedback('');
    try {
      await apiFetch('/api/v1/settings/filter-rules', {
        method: 'POST',
        body: newRule,
        token,
      });
      setNewRule({ rule_type: 'blacklist_word', pattern: '', description: '' });
      await load();
      setFeedback('Правило фильтрации добавлено.');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось добавить правило.');
    } finally {
      setBusy('');
    }
  };

  const deleteRule = async (id: number) => {
    setBusy(`rule-${id}`);
    setFeedback('');
    try {
      await apiFetch(`/api/v1/settings/filter-rules/${id}`, {
        method: 'DELETE',
        token,
      });
      await load();
      setFeedback('Правило фильтрации удалено.');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось удалить правило.');
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="max-w-5xl space-y-8 pb-20">
      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-bold">Рабочие настройки</h3>
          <p className="mt-1 text-sm text-neutral-500">
            Здесь оставлены только реально работающие настройки, которые влияют на сбор источников.
          </p>
        </div>

        <Card className="p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100">
              <Clock3 className="h-5 w-5 text-neutral-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold">Интервал парсинга новостей</p>
              <p className="mt-1 text-xs text-neutral-500">
                Значение в минутах. Подходит для сезонной настройки частоты сбора.
              </p>
              <div className="mt-4 flex max-w-md items-center gap-3">
                <input
                  type="number"
                  min={5}
                  max={1440}
                  value={intervalValue}
                  onChange={(event) => setIntervalValue(event.target.value)}
                  className="w-40 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm outline-none focus:border-black/30"
                />
                <span className="text-sm text-neutral-500">минут</span>
                <Button disabled={Boolean(busy)} onClick={saveInterval}>
                  Сохранить
                </Button>
              </div>
              <p className="mt-2 text-xs text-neutral-400">
                Текущее значение в базе: {settingValue(settings, 'collection_interval_minutes', '60')}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100">
              <KeyRound className="h-5 w-5 text-neutral-500" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold">VK access token для сбора</p>
              <p className="mt-1 text-xs text-neutral-500">
                Сюда вставляется только сам токен. Без частей вида <span className="font-mono">expires_in</span> и{' '}
                <span className="font-mono">user_id</span>.
              </p>
              <div className="mt-4 flex flex-col gap-3">
                <input
                  value={vkToken}
                  onChange={(event) => setVkToken(event.target.value)}
                  placeholder="vk1.a...."
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm outline-none focus:border-black/30"
                />
                <div className="flex items-center gap-3">
                  <Button disabled={Boolean(busy)} onClick={saveVkToken}>
                    Сохранить VK token
                  </Button>
                  <span className="text-xs text-neutral-400">
                    В базе сейчас: {settingValue(settings, 'vk_access_token') ? 'сохранен' : 'не задан'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-bold">Telegram-авторизация для сбора</h3>
          <p className="mt-1 text-sm text-neutral-500">
            Встроенный вход в Telegram для получения API ID, API HASH и session string без ручных скриптов.
          </p>
        </div>

        <Card className="space-y-4 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">API ID</label>
              <input
                value={telegramAuth.api_id}
                onChange={(event) => setTelegramAuth({ ...telegramAuth, api_id: event.target.value })}
                className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">API HASH</label>
              <input
                value={telegramAuth.api_hash}
                onChange={(event) => setTelegramAuth({ ...telegramAuth, api_hash: event.target.value })}
                className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Номер телефона</label>
              <input
                value={telegramAuth.phone}
                onChange={(event) => setTelegramAuth({ ...telegramAuth, phone: event.target.value })}
                placeholder="+7..."
                className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              />
            </div>
            <div className="flex items-end">
              <Button
                disabled={Boolean(busy) || !telegramAuth.api_id || !telegramAuth.api_hash || !telegramAuth.phone}
                onClick={sendTelegramCode}
              >
                Отправить код
              </Button>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Код из Telegram</label>
              <input
                value={telegramAuth.code}
                onChange={(event) => setTelegramAuth({ ...telegramAuth, code: event.target.value })}
                className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase text-neutral-400">Пароль 2FA</label>
              <input
                type="password"
                value={telegramAuth.password}
                onChange={(event) => setTelegramAuth({ ...telegramAuth, password: event.target.value })}
                className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-black"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={Boolean(busy) || !telegramAuth.api_id || !telegramAuth.api_hash} onClick={startTelegramQrAuth}>
              Войти через QR
            </Button>
            <Button variant="outline" disabled={Boolean(busy) || !telegramAuth.code} onClick={completeTelegramAuth}>
              Сохранить Telegram-сессию
            </Button>
            <span className="text-xs text-neutral-500">
              QR-вход проще. Вход по коду оставлен как запасной вариант.
            </span>
          </div>

          {telegramQr.qr_svg && (
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
              <p className="mb-3 text-xs font-bold uppercase text-neutral-400">QR-вход в Telegram</p>
              <div className="inline-block rounded-xl bg-white p-3" dangerouslySetInnerHTML={{ __html: telegramQr.qr_svg }} />
              <p className="mt-3 text-xs text-neutral-500">
                Telegram → Настройки → Устройства → Подключить устройство. После подтверждения сессия сохранится автоматически.
              </p>
            </div>
          )}

          {telegramSessionPreview && (
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
              <p className="mb-2 text-xs font-bold uppercase text-neutral-400">Session string</p>
              <textarea
                readOnly
                value={telegramSessionPreview}
                className="min-h-28 w-full rounded-lg border border-neutral-200 bg-white p-3 text-xs outline-none"
              />
            </div>
          )}
        </Card>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-bold">Туториал по Telegram и VK</h3>
          <p className="mt-1 text-sm text-neutral-500">
            Короткие шаги, чтобы технично и без боли собрать нужные токены, айди и хэши.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="space-y-4 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100">
                <MessageCircleMore className="h-5 w-5 text-neutral-500" />
              </div>
              <div>
                <p className="text-sm font-bold">Как получить Telegram API ID / API HASH</p>
                <p className="text-xs text-neutral-500">Нужно один раз создать приложение Telegram.</p>
              </div>
            </div>
            <ol className="space-y-2 text-sm text-neutral-700">
              <li>
                1. Открой{' '}
                <a
                  href="https://my.telegram.org"
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-black underline underline-offset-2"
                >
                  my.telegram.org
                </a>{' '}
                и войди по номеру телефона.
              </li>
              <li>2. Перейди в `API development tools`.</li>
              <li>3. Создай приложение с любым названием.</li>
              <li>4. Скопируй `api_id` и `api_hash`.</li>
              <li>5. Вставь их в поля выше и используй QR-вход, чтобы система сама сохранила `session string`.</li>
            </ol>
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
              <p className="font-semibold text-neutral-700">Что нужно получить вручную</p>
              <p className="mt-1 font-mono text-[11px]">API ID</p>
              <p className="font-mono text-[11px]">API HASH</p>
              <p className="mt-3 font-semibold text-neutral-700">Что система сделает сама</p>
              <p className="mt-1 font-mono text-[11px]">TELEGRAM_SESSION_STRING</p>
              <p className="mt-3">
                Важно: session string вручную вытаскивать больше не нужно. После QR-входа она сохранится в настройках автоматически.
              </p>
            </div>
          </Card>

          <Card className="space-y-4 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100">
                <KeyRound className="h-5 w-5 text-neutral-500" />
              </div>
              <div>
                <p className="text-sm font-bold">Как получить VK access token</p>
                <p className="text-xs text-neutral-500">Для сбора постов из VK нужен обычный access token.</p>
              </div>
            </div>
            <ol className="space-y-2 text-sm text-neutral-700">
              <li>
                1. Открой страницу получения VK access token:{' '}
                <a
                  href="https://oauth.vk.com/authorize?client_id=6287487&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=wall,groups,offline&response_type=token&v=5.131"
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-black underline underline-offset-2"
                >
                  открыть страницу VK OAuth
                </a>
                .
              </li>
              <li>2. После авторизации скопируй значение access token формата `vk1.a....`.</li>
              <li>3. Если VK вернул строку вида `vk1.a....&expires_in=0&user_id=...`, бери только часть до `&expires_in`.</li>
              <li>4. Вставь только сам токен в поле `VK access token` выше и сохрани.</li>
              <li>5. Для источника в поле VK домен указывай не полную ссылку, а короткое имя после `vk.com/`.</li>
            </ol>
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
              <p className="font-semibold text-neutral-700">Что вставлять в админку</p>
              <p className="mt-1 font-mono text-[11px]">vk1.a.ABCDEFG...</p>
              <p className="mt-3 font-semibold text-neutral-700">Что не вставлять в админку</p>
              <p className="mt-1 font-mono text-[11px]">vk1.a.ABCDEFG...&amp;expires_in=0&amp;user_id=123456</p>
              <p className="mt-3">
                Пример источника: из `https://vk.com/vympel_rybinsk` в поле источника нужно писать `vympel_rybinsk`.
              </p>
            </div>
          </Card>
        </div>
      </section>

      <section>
        <div className="mb-5">
          <h3 className="text-lg font-bold">Правила фильтрации</h3>
          <p className="mt-1 text-sm text-neutral-500">
            Управление blacklist и дополнительными правилами очистки потока.
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
                    <p className="text-sm font-bold">
                      {ruleTypeLabel(rule.rule_type)}: {rule.pattern}
                    </p>
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

          <Button type="submit" disabled={Boolean(busy)}>
            Добавить правило
          </Button>
        </form>
      </section>

      {feedback && <Card className="p-4 text-sm text-neutral-700">{feedback}</Card>}
    </div>
  );
}
