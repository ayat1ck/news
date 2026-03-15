import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

function isLocalHost(hostname: string) {
  return hostname === 'localhost' || hostname === '127.0.0.1';
}

function isAdminHost(hostname: string) {
  const configured = process.env.NEXT_PUBLIC_ADMIN_HOST;
  if (configured) return hostname === configured;
  return false;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hostname = request.headers.get('host')?.split(':')[0] || '';
  const url = request.nextUrl.clone();
  const adminHost = isAdminHost(hostname);
  const localHost = isLocalHost(hostname);

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next();
  }

  if (adminHost) {
    if (pathname === '/') {
      url.pathname = '/admin';
      return NextResponse.rewrite(url);
    }
    if (pathname === '/login') {
      url.pathname = '/admin/login';
      return NextResponse.rewrite(url);
    }
    if (pathname === '/console') {
      url.pathname = '/admin/login';
      return NextResponse.rewrite(url);
    }
    if (pathname.startsWith('/article') || pathname === '/admin/login') {
      url.pathname = '/login';
      return pathname === '/admin/login' ? NextResponse.redirect(url) : NextResponse.redirect(new URL('/', `${request.nextUrl.protocol}//${process.env.NEXT_PUBLIC_SITE_HOST || hostname}${search}`));
    }
    if (!pathname.startsWith('/admin')) {
      url.pathname = '/admin';
      return NextResponse.rewrite(url);
    }
    return NextResponse.next();
  }

  if (pathname.startsWith('/admin') || pathname === '/login') {
    if (process.env.NEXT_PUBLIC_SITE_URL) {
      return NextResponse.redirect(new URL('/', process.env.NEXT_PUBLIC_SITE_URL));
    }
    url.pathname = '/';
    return NextResponse.redirect(url);
  }

  if (pathname === '/console' && !localHost) {
    if (process.env.NEXT_PUBLIC_SITE_URL) {
      return NextResponse.redirect(new URL('/', process.env.NEXT_PUBLIC_SITE_URL));
    }
    url.pathname = '/';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!.*\\..*).*)'],
};
