'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';

interface ArticleCardProps {
  id: number;
  slug: string | null;
  headline: string | null;
  summary: string | null;
  tags: string | null;
  published_at: string | null;
  media_url?: string | null;
  isHero?: boolean;
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 24) return `${hours} ч. назад`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Вчера';
  if (days < 7) return `${days} дн. назад`;
  return d.toLocaleDateString();
}

export function ArticleCard({
  id,
  slug,
  headline,
  summary,
  tags,
  published_at,
  media_url,
  isHero = false,
}: ArticleCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const href = `/article/${slug || id}`;
  const tag = tags?.split(',')[0]?.trim() || 'Новости';
  const imgSrc = media_url || 'https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?auto=format&fit=crop&q=80&w=800';

  return (
    <Link href={href} className={`group cursor-pointer block ${isHero ? 'md:grid md:grid-cols-2 gap-8 mb-12' : ''}`}>
      <div className={`relative overflow-hidden rounded-2xl bg-neutral-100 aspect-[16/9] ${!isHero ? 'mb-4' : ''}`}>
        {!imageFailed ? (
          <img
            src={imgSrc}
            alt={headline || ''}
            className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-neutral-200 text-xs font-bold uppercase tracking-[0.3em] text-neutral-500">
            Newsflux
          </div>
        )}
        <div className="absolute top-4 left-4">
          <Badge variant="success" className="bg-white/90 backdrop-blur shadow-sm">
            {tag}
          </Badge>
        </div>
      </div>
      <div className="flex flex-col justify-center py-2">
        <div className="flex items-center gap-3 mb-3 text-xs text-neutral-400 font-medium uppercase tracking-wide">
          <span>{formatDate(published_at)}</span>
        </div>
        <h2
          className={`${isHero ? 'text-3xl md:text-5xl' : 'text-xl'} font-bold leading-tight mb-3 group-hover:text-neutral-600 transition-colors`}
        >
          {headline || 'Без заголовка'}
        </h2>
        <p className="text-neutral-500 text-sm md:text-base leading-relaxed line-clamp-2">
          {summary || ''}
        </p>
      </div>
    </Link>
  );
}
