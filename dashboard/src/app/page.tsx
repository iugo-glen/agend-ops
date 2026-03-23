import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import { KanbanBoard } from '@/components/KanbanBoard';

export default async function HomePage() {
  const session = await auth();
  if (!session?.user) redirect('/login');

  return <KanbanBoard />;
}
