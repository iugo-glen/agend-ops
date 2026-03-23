import { auth, signOut } from '@/auth';
import { redirect } from 'next/navigation';

export default async function HomePage() {
  const session = await auth();
  if (!session?.user) redirect('/login');

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface p-8">
      <h1 className="text-display font-semibold text-text-primary">
        Welcome, {session.user.name}
      </h1>
      <p className="text-body text-text-secondary">Dashboard loading...</p>
      <form
        action={async () => {
          'use server';
          await signOut({ redirectTo: '/login' });
        }}
      >
        <button
          type="submit"
          className="rounded-lg border border-border-default bg-surface-secondary px-4 py-2 text-body text-text-primary transition-opacity hover:opacity-80"
          style={{ minHeight: '44px' }}
        >
          Sign out
        </button>
      </form>
    </main>
  );
}
