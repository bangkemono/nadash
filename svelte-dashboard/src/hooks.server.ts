import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  const origin = event.request.headers.get('origin');
  
  if (event.request.method === 'POST' && origin) {
     const allowedOrigins = [
         'http://localhost:8080',
         'http://127.0.0.1:8080',
     ];

     if (allowedOrigins.some(o => origin.startsWith(o))) {
         event.request.headers.set('origin', event.url.origin);
     }
  }

  return await resolve(event);
};
