'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { PublicHeader } from '@/components/public/PublicHeader';
import { PublicFooter } from '@/components/public/PublicFooter';
import { ArticleCard } from '@/components/public/ArticleCard';
import { Button } from '@/components/ui/Button';
import { apiFetch } from '@/lib/api';

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

interface Article {
  id: number;
  headline: string | null;
  summary: string | null;
  slug: string | null;
  tags: string | null;
  topics: string | null;
  published_at: string | null;
  media_url?: string | null;
}
interface ListResponse {
  items: Article[];
  total: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  general: 'Главная',
  industry: 'Промышленность',
  transport: 'Транспорт',
  business: 'Бизнес',
  technology: 'Технологии',
  science: 'Наука',
  politics: 'Политика',
  defense: 'Оборона',
  energy: 'Энергетика',
  society: 'Общество',
  culture: 'Культура',
  world: 'Мир',
  sports: 'Спорт',
  education: 'Образование',
};

export function HomeContent() {
  const searchParams = useSearchParams();
  const topic = searchParams.get('topic');
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    const params = new URLSearchParams({ page_size: '20' });
    if (topic) params.set('topic', topic);
    apiFetch<ListResponse>(`/api/public/articles?${params.toString()}`)
      .then((data) => setArticles(data.items))
      .catch(console.error);
  }, [topic]);

  const featured = articles[0];
  const others = articles.slice(1);
  const currentLabel = topic ? (CATEGORY_LABELS[topic] || topic) : null;

  return (
    <div className="min-h-screen bg-white text-neutral-900 font-sans selection:bg-neutral-900 selection:text-white">
      <PublicHeader />
      <main className="max-w-7xl mx-auto px-6 py-12">
        {currentLabel && (
          <div className="mb-10 flex items-center gap-2">
            <a href="/" className="text-neutral-400 hover:text-black">
              Главная
            </a>
            <ChevronRightIcon className="w-4 h-4 text-neutral-300" />
            <span className="font-bold">{currentLabel}</span>
          </div>
        )}

        {featured && (
          <ArticleCard
            id={featured.id}
            slug={featured.slug}
            headline={featured.headline}
            summary={featured.summary}
            tags={featured.topics || featured.tags}
            published_at={featured.published_at}
            media_url={featured.media_url}
            isHero
          />
        )}

        <div className="flex items-center justify-between mb-8 border-b border-neutral-100 pb-4">
          <h3 className="text-xl font-bold">
            {currentLabel ? `Новости: ${currentLabel}` : 'Последние новости'}
          </h3>
          <div className="flex gap-4">
            <Button variant="ghost" className="text-xs">
              По дате
            </Button>
            <Button variant="ghost" className="text-xs text-neutral-400">
              По теме
            </Button>
          </div>
        </div>

        {articles.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-10 gap-y-12">
            {others.map((article) => (
              <ArticleCard
                key={article.id}
                id={article.id}
                slug={article.slug}
                headline={article.headline}
                summary={article.summary}
                tags={article.topics || article.tags}
                published_at={article.published_at}
                media_url={article.media_url}
              />
            ))}
          </div>
        ) : (
          <div className="py-20 text-center border-2 border-dashed border-neutral-100 rounded-3xl">
            <p className="text-neutral-400">Пока нет опубликованных статей в этой категории.</p>
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
