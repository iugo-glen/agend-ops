'use client';

import { signIn } from 'next-auth/react';

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <div className="w-full max-w-sm rounded-lg border border-border-default bg-surface-secondary p-8 text-center">
        <h1 className="mb-2 text-display font-semibold text-text-primary">
          Agend Ops
        </h1>
        <p className="mb-8 text-body text-text-secondary">
          Operations Dashboard
        </p>
        <button
          onClick={() => signIn('google', { callbackUrl: '/' })}
          className="w-full rounded-lg bg-accent px-4 py-3 text-body font-semibold text-white transition-opacity hover:opacity-90"
          style={{ minHeight: '44px' }}
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
