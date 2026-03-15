'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { PublicHeader } from '@/components/public/PublicHeader';
import { PublicFooter } from '@/components/public/PublicFooter';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiFetch } from '@/lib/api';
import { Send, MessageSquare } from 'lucide-react';

interface Article {
  id: number;
  headline: string | null;
  summary: string | null;
  body: string | null;
  slug: string | null;
  tags: string | null;
  published_at: string | null;
  media_url?: string | null;
  source_url?: string | null;
}

interface ListResponse {
  items: Article[];
  total: number;
}

type BodyBlock =
  | { type: 'heading'; content: string }
  | { type: 'paragraph'; content: string };

function parseBody(body: string | null): BodyBlock[] {
  if (!body) return [];

  return body
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const compact = block.replace(/\s+/g, ' ').trim();
      if (compact.length <= 90 && !/[.!?]$/.test(compact)) {
        return { type: 'heading', content: compact } satisfies BodyBlock;
      }
      return { type: 'paragraph', content: compact } satisfies BodyBlock;
    });
}

function normalizeCmp(value: string | null | undefined): string {
  return (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

export default function ArticlePage() {
  const params = useParams();
  const [article, setArticle] = useState<Article | null>(null);
  const [related, setRelated] = useState<Article[]>([]);
  const [error, setError] = useState('');
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    if (!params.slug) return;
    apiFetch<Article>(`/api/public/articles/${params.slug}`)
      .then((a) => {
        setArticle(a);
        return apiFetch<ListResponse>('/api/public/articles?page_size=5');
      })
      .then((data) => {
        const slugId = typeof params.slug === 'string' ? params.slug : '';
        setRelated(data.items.filter((a) => String(a.slug || a.id) !== slugId));
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка'));
  }, [params.slug]);

  if (error)
    return (
      <div className="min-h-screen bg-white">
        <PublicHeader />
        <main className="max-w-7xl mx-auto px-6 py-16">
          <div className="bg-red-50 border border-red-100 rounded-xl p-6 text-red-700">Статья не найдена</div>
          <Link href="/" className="inline-block mt-4 text-neutral-600 hover:text-black">
            ← На главную
          </Link>
        </main>
      </div>
    );

  if (!article)
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="text-neutral-500">Загрузка...</p>
      </div>
    );

  const tag = article.tags?.split(',')[0]?.trim() || 'Новости';
  const tagList = article.tags?.split(',').map((t) => t.trim()).filter(Boolean) || [];
  const bodyBlocks = parseBody(article.body).filter((block, index, all) => {
    const cmp = normalizeCmp(block.content);
    if (!cmp) return false;
    if (cmp === normalizeCmp(article.headline) || cmp === normalizeCmp(article.summary)) return false;
    return !all.slice(0, index).some((item) => normalizeCmp(item.content) === cmp);
  });

  return (
    <div className="min-h-screen bg-white text-neutral-900 selection:bg-neutral-900 selection:text-white">
      <PublicHeader />
      <main className="max-w-7xl mx-auto px-6 py-16 grid lg:grid-cols-12 gap-16">
        <div className="lg:col-span-8">
          <div className="mb-10">
            <Badge variant="success" className="mb-6">
              {tag}
            </Badge>
            <h1 className="text-4xl md:text-6xl font-black mb-8 leading-[1.1] tracking-tight">
              {article.headline || 'Без заголовка'}
            </h1>
            {article.summary && (
              <p className="text-2xl text-neutral-500 mb-10 leading-relaxed italic border-l-4 border-neutral-100 pl-6">
                {article.summary}
              </p>
            )}
            <div className="flex items-center gap-4 py-8 border-y border-neutral-100">
              <div className="w-12 h-12 rounded-full bg-neutral-900 flex items-center justify-center text-white font-bold">
                N
              </div>
              <div className="flex-1">
                <p className="font-bold text-base">Newsflux</p>
                <p className="text-xs text-neutral-400 uppercase tracking-widest">
                  {article.published_at
                    ? new Date(article.published_at).toLocaleDateString('ru-RU', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      })
                    : ''}{' '}
                  • 5 мин чтения
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="p-2 h-10 w-10 justify-center">
                  <Send className="w-4 h-4" />
                </Button>
                <Button variant="outline" className="p-2 h-10 w-10 justify-center">
                  <MessageSquare className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          <div className="max-w-3xl mx-auto">
            {article.media_url && !imageFailed && (
              <div className="mb-10 overflow-hidden rounded-[2rem] border border-neutral-100 bg-neutral-100">
                <img
                  src={article.media_url}
                  alt={article.headline || 'Article image'}
                  className="h-auto max-h-[34rem] w-full object-cover"
                  onError={() => setImageFailed(true)}
                />
              </div>
            )}

            <div className="space-y-6">
              {bodyBlocks.length > 0 ? (
                bodyBlocks.map((block, index) =>
                  block.type === 'heading' ? (
                    <h2 key={`${block.type}-${index}`} className="pt-4 text-2xl font-bold tracking-tight text-neutral-900">
                      {block.content}
                    </h2>
                  ) : (
                    <p key={`${block.type}-${index}`} className="text-xl leading-[1.8] text-neutral-800">
                      {block.content}
                    </p>
                  ),
                )
              ) : (
                <p className="text-xl leading-[1.8] text-neutral-800">Текст статьи пока недоступен.</p>
              )}
            </div>

            {article.source_url && (
              <div className="mt-10 rounded-2xl border border-neutral-100 bg-neutral-50 p-5 text-sm text-neutral-600">
                Первоисточник:{' '}
                <a
                  href={article.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-neutral-900 underline decoration-neutral-300 underline-offset-4"
                >
                  открыть оригинал
                </a>
              </div>
            )}

            {tagList.length > 0 && (
              <div className="mt-20 pt-10 border-t border-neutral-100">
                <h4 className="font-bold mb-6">Теги статьи:</h4>
                <div className="flex gap-2 flex-wrap">
                  {tagList.map((t) => (
                    <span
                      key={t}
                      className="px-4 py-2 bg-neutral-50 rounded-full text-sm hover:bg-neutral-100 cursor-pointer transition-colors"
                    >
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <aside className="lg:col-span-4 space-y-12 h-fit sticky top-24">
          <div>
            <h4 className="text-sm font-bold uppercase tracking-widest text-neutral-400 mb-6 pb-2 border-b border-neutral-100">
              Похожие новости
            </h4>
            <div className="space-y-8">
              {related.slice(0, 3).map((a) => (
                <Link key={a.id} href={`/article/${a.slug || a.id}`} className="group cursor-pointer flex gap-4">
                  <div className="w-24 h-24 rounded-xl bg-neutral-100 overflow-hidden shrink-0">
                    {a.media_url ? (
                      <img src={a.media_url} alt={a.headline || ''} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-neutral-200" />
                    )}
                  </div>
                  <div>
                    <Badge variant="default" className="mb-2">
                      {a.tags?.split(',')[0]?.trim() || 'Новости'}
                    </Badge>
                    <h5 className="font-bold text-sm leading-snug group-hover:underline">
                      {a.headline || 'Без заголовка'}
                    </h5>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <Card className="p-6 bg-black text-white border-none">
            <h4 className="font-bold text-xl mb-4">Подпишитесь на рассылку</h4>
            <p className="text-neutral-400 text-sm mb-6">
              Получайте 5 главных новостей дня каждое утро прямо на почту.
            </p>
            <input
              type="email"
              placeholder="email@example.com"
              className="w-full p-3 bg-neutral-900 border border-neutral-800 rounded-lg text-sm mb-4 outline-none focus:border-neutral-600"
            />
            <Button variant="secondary" className="w-full justify-center bg-neutral-100 text-neutral-900 hover:bg-neutral-200">
              Подписаться
            </Button>
          </Card>
        </aside>
      </main>
      <PublicFooter />
    </div>
  );
}
