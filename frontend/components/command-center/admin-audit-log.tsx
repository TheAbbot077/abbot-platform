"use client";

import { useEffect, useState } from "react";
import { Loader2, Search, ShieldCheck } from "lucide-react";

import { getAdminAuditLogs } from "@/lib/api";
import type { AdminAuditLog, AdminAuditLogResponse } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const actionOptions = [
  "user_deactivate",
  "user_reactivate",
  "textbook_deleted",
  "subject_deleted",
  "lesson_restart",
  "chapter_restart",
  "textbook_restart",
  "textbook_reprocess_queued",
  "mcq_regenerated",
  "tutor_lesson_regenerated",
];

export function AdminAuditLogPanel() {
  const [auditLogs, setAuditLogs] = useState<AdminAuditLogResponse | null>(null);
  const [query, setQuery] = useState("");
  const [action, setAction] = useState("");
  const [targetType, setTargetType] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadAuditLogs() {
    setIsLoading(true);
    setError(null);
    try {
      setAuditLogs(await getAdminAuditLogs({ q: query, action, targetType }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load audit logs.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadAuditLogs();
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query, action, targetType]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Admin audit log</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Review sensitive actions across users, textbooks, lessons, and quality tools.</p>
          </div>
          <div className="text-sm text-muted-foreground">{auditLogs?.total_count.toLocaleString() ?? 0} events found</div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 lg:grid-cols-[1fr_220px_180px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              className="h-11 w-full rounded-xl border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search description, admin, target, or action"
            />
          </label>
          <select
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={action}
            onChange={(event) => setAction(event.target.value)}
          >
            <option value="">All actions</option>
            {actionOptions.map((option) => (
              <option key={option} value={option}>{friendlyAction(option)}</option>
            ))}
          </select>
          <select
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={targetType}
            onChange={(event) => setTargetType(event.target.value)}
          >
            <option value="">All targets</option>
            <option value="user">Users</option>
            <option value="subject">Subjects</option>
            <option value="document">Textbooks</option>
            <option value="chapter">Chapters</option>
            <option value="concept">Concepts</option>
          </select>
        </div>

        {error ? <p className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p> : null}

        <AuditLogTable logs={auditLogs?.logs ?? []} isLoading={isLoading} />
      </CardContent>
    </Card>
  );
}

function AuditLogTable({ logs, isLoading }: { logs: AdminAuditLog[]; isLoading: boolean }) {
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-3 font-semibold">Action</th>
            <th className="px-3 py-3 font-semibold">Description</th>
            <th className="px-3 py-3 font-semibold">Admin</th>
            <th className="px-3 py-3 font-semibold">Target</th>
            <th className="px-3 py-3 font-semibold">When</th>
            <th className="px-3 py-3 font-semibold">IP</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td className="px-3 py-6 text-muted-foreground" colSpan={6}>
                <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
                Loading audit trail...
              </td>
            </tr>
          ) : logs.length === 0 ? (
            <tr>
              <td className="px-3 py-6 text-muted-foreground" colSpan={6}>No audit events match these filters.</td>
            </tr>
          ) : (
            logs.map((log) => (
              <tr key={log.id} className="border-t">
                <td className="px-3 py-3">
                  <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                    <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    {friendlyAction(log.action)}
                  </span>
                </td>
                <td className="px-3 py-3">
                  <p>{log.description}</p>
                  {Object.keys(log.metadata).length > 0 ? (
                    <p className="mt-1 max-w-xl truncate text-xs text-muted-foreground">{JSON.stringify(log.metadata)}</p>
                  ) : null}
                </td>
                <td className="px-3 py-3">{log.admin_username ?? "Unknown"}</td>
                <td className="px-3 py-3">{log.target_type}:{log.target_id || "n/a"}</td>
                <td className="px-3 py-3">{formatDate(log.created_at)}</td>
                <td className="px-3 py-3">{log.ip_address ?? "Not recorded"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function friendlyAction(value: string): string {
  return value.replaceAll("_", " ");
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
