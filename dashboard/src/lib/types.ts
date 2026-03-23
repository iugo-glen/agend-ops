// TypeScript interfaces derived from JSON schemas in /schemas/

export interface FeedEntry {
  ts: string;
  type: 'triage' | 'task' | 'draft' | 'system' | 'command' | 'briefing' | 'todo';
  summary: string;
  level: 'critical' | 'info' | 'debug';
  trigger: 'manual' | 'scheduled' | 'hook';
  details?: Record<string, unknown>;
  duration_ms?: number;
}

export interface TriageRecord {
  message_id: string;
  thread_id: string;
  from: string;
  from_name?: string;
  subject: string;
  received: string;
  category?: 'client' | 'team' | 'sales' | 'admin' | 'noise';
  priority: 'urgent' | 'needs-response' | 'informational' | 'low-priority';
  starred?: boolean;
  has_attachments?: boolean;
  snippet?: string;
  action_items?: string[];
  suggested_action?: 'draft-reply' | 'review-attachment' | 'forward-to-team' | 'archive' | 'none';
  client_name?: string;
  client_domain?: string;
  action_type?: 'contract' | 'invoice' | 'meeting' | 'deadline' | 'none';
  draft_id?: string;
}

export interface TaskRecord {
  id: string;
  ts: string;
  status: 'pending' | 'in-progress' | 'completed' | 'cancelled';
  description: string;
  trigger: 'manual' | 'triage-suggestion';
  source_email?: string | null;
  outcome?: string | null;
  completed_at?: string | null;
  task_type?: 'contract-review' | 'meeting-prep' | 'document-summary' | 'draft-comms' | null;
  output_dir?: string | null;
  source_triage?: string | null;
  client_name?: string | null;
  draft_id?: string | null;
}

export interface TodoRecord {
  id: string;
  ts: string;
  status: 'active' | 'completed';
  text: string;
  priority: 'high' | 'normal' | 'low';
  trigger: 'manual' | 'recurring';
  due_date?: string | null;
  category?: 'business' | 'personal' | 'marketing' | null;
  recurring?: 'daily' | 'weekly' | 'weekdays' | null;
  completed_at?: string | null;
  linked_task_id?: string | null;
}

export interface InvoiceRecord {
  id: string;
  ts: string;
  status: 'reminder' | 'draft' | 'sent' | 'paid' | 'disputed' | 'written-off';
  client_name: string;
  amount?: number | null;
  currency?: string;
  tax_amount?: number | null;
  due_date?: string | null;
  description?: string | null;
  invoice_number?: string | null;
  po_number?: string | null;
  project_code?: string | null;
  payment_terms?: string | null;
  source_email_id?: string | null;
  xero_invoice_id?: string | null;
  trigger: 'manual' | 'triage-suggestion' | 'xero-sync';
  amount_paid?: number | null;
  completed_at?: string | null;
}

export interface QueuedAction {
  id: string;
  ts: string;
  action: 'mark-paid' | 'complete-todo' | 'complete-task' | 'trigger-triage';
  target_id: string;
  status: 'queued' | 'completed' | 'failed';
  requested_by: string;
  processed_at?: string;
  result?: string;
}
