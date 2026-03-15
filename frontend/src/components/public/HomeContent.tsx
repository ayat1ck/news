'use client';

import { useEffect, useState, useMemo } from 'react';
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
  published_at: string | null;
  media_url?: string | null;
}
interface ListResponse {
  items: Article[];
  total: number;
}

const CATEGORIES = ['Технологии', 'Бизнес', 'Наука', 'Дизайн', 'AI', 'Крипто'];

export function HomeContent() {
  const searchParams = useSearchParams();
  const categoryParam = searchParams.get('category');
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    apiFetch<ListResponse>('/api/public/articles?page_size=20')
      .then((data) => setArticles(data.items))
      .catch(console.error);
  }, []);

  const currentCategory = categoryParam && CATEGORIES.includes(categoryParam) ? categoryParam : null;
  const filteredArticles = useMemo(() => {
    if (!currentCategory) return articles;
    return articles.filter((a) => a.tags?.toLowerCase().includes(currentCategory.toLowerCase()));
  }, [articles, currentCategory]);

  const featured = filteredArticles[0];
  const others = filteredArticles.slice(1);

  return (
    <div className="min-h-screen bg-white text-neutral-900 font-sans selection:bg-neutral-900 selection:text-white">
      <PublicHeader />
      <main className="max-w-7xl mx-auto px-6 py-12">
        {currentCategory && (
          <div className="mb-10 flex items-center gap-2">
            <a href="/" className="text-neutral-400 hover:text-black">
              Главная
            </a>
            <ChevronRightIcon className="w-4 h-4 text-neutral-300" />
            <span className="font-bold">{currentCategory}</span>
          </div>
        )}

        {featured && (
          <ArticleCard
            id={featured.id}
            slug={featured.slug}
            headline={featured.headline}
            summary={featured.summary}
            tags={featured.tags}
            published_at={featured.published_at}
            media_url={featured.media_url}
            isHero
          />
        )}

        <div className="flex items-center justify-between mb-8 border-b border-neutral-100 pb-4">
          <h3 className="text-xl font-bold">
            {currentCategory ? `Все в ${currentCategory}` : 'Последние новости'}
          </h3>
          <div className="flex gap-4">
            <Button variant="ghost" className="text-xs">
              По дате
            </Button>
            <Button variant="ghost" className="text-xs text-neutral-400">
              Популярное
            </Button>
          </div>
        </div>

        {filteredArticles.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-x-10 gap-y-12">
            {others.map((article) => (
              <ArticleCard
                key={article.id}
                id={article.id}
                slug={article.slug}
                headline={article.headline}
                summary={article.summary}
                tags={article.tags}
                published_at={article.published_at}
                media_url={article.media_url}
              />
            ))}
          </div>
        ) : (
          <div className="py-20 text-center border-2 border-dashed border-neutral-100 rounded-3xl">
            <p className="text-neutral-400">
              {articles.length === 0 ? 'Пока нет опубликованных статей.' : 'В этой категории пока нет новостей.'}
            </p>
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}
