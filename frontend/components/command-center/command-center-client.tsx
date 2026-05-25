"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, BookOpen, Database, GraduationCap, Users } from "lucide-react";

import { getCommandCenterDashboard } from "@/lib/api";
import type { CommandCenterDashboard, CommandCenterMetric } from "@/lib/types";
import { AdminQualityTools } from "@/components/command-center/admin-quality-tools";
import { AdminTextbookManagement } from "@/components/command-center/admin-textbook-management";
import { AdminUserManagement } from "@/components/command-center/admin-user-management";
import { AdminUserAnalyticsPanel } from "@/components/command-center/admin-user-analytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const metricIcons: Record<string, typeof Users> = {
  total_users: Users,
  total_subjects: GraduationCap,
  total_documents: BookOpen,
  total_chapters: Database,
  total_concepts: Database,
  total_quiz_attempts: Database,
  total_tutor_sessions: Database,
  failed_document_processing_count: AlertTriangle,
  low_confidence_parser_count: AlertTriangle,
};

export function CommandCenterClient() {
  const [dashboard, setDashboard] = useState<CommandCenterDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadCommandCenter() {
      try {
        const response = await getCommandCenterDashboard();
        if (isMounted) {
          setDashboard(response);
        }
      } catch (caught) {
        if (isMounted) {
          setError(caught instanceof Error ? caught.message : "Unable to load Abbot Command Center.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadCommandCenter();

    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return <div className="rounded-2xl border bg-card p-8 text-sm text-muted-foreground">Opening Abbot Command Center...</div>;
  }

  if (error) {
    return (
      <Card className="border-destructive/40">
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold">Command Center unavailable</h2>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!dashboard) {
    return null;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {dashboard.metrics.map((metric) => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </section>

      <div className="rounded-2xl border bg-card p-4 text-sm shadow-sm">
        <Link className="font-medium text-primary hover:underline" href="/command-center/audit">
          Open admin audit log
        </Link>
        <span className="ml-2 text-muted-foreground">Track sensitive changes and quality-tool actions.</span>
      </div>

      <section className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Recent uploaded textbooks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 md:hidden">
              {dashboard.recent_uploaded_textbooks.map((document) => (
                <div key={document.id} className="rounded-2xl border bg-background p-4 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-words font-semibold">{document.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{document.subject_name ?? "No subject"}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-muted px-2 py-1 text-xs font-semibold">
                      {friendlyStatus(document.status)}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground">
                    <p>Owner: <span className="font-medium text-foreground">{document.owner_username}</span></p>
                    <p>Parser: <span className="font-medium text-foreground">{document.parser_strategy ?? "Not recorded"}</span></p>
                    <p>Confidence: <span className="font-medium text-foreground">{formatConfidence(document.parser_confidence_score)}</span></p>
                    <p>Uploaded: <span className="font-medium text-foreground">{formatDate(document.created_at)}</span></p>
                  </div>
                </div>
              ))}
            </div>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-3 font-semibold">Textbook</th>
                    <th className="pb-3 font-semibold">Owner</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Parser</th>
                    <th className="pb-3 font-semibold">Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.recent_uploaded_textbooks.map((document) => (
                    <tr key={document.id} className="border-t">
                      <td className="py-3 pr-4">
                        <p className="font-medium">{document.title}</p>
                        <p className="text-xs text-muted-foreground">{document.subject_name ?? "No subject"}</p>
                      </td>
                      <td className="py-3 pr-4">{document.owner_username}</td>
                      <td className="py-3 pr-4">{friendlyStatus(document.status)}</td>
                      <td className="py-3 pr-4">
                        <p>{document.parser_strategy ?? "Not recorded"}</p>
                        <p className="text-xs text-muted-foreground">{formatConfidence(document.parser_confidence_score)}</p>
                      </td>
                      <td className="py-3">{formatDate(document.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent failed jobs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.recent_failed_jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No failed textbook prep jobs right now.</p>
            ) : (
              dashboard.recent_failed_jobs.map((job) => (
                <div key={job.document_id} className="rounded-xl border bg-background p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{job.title}</p>
                      <p className="text-xs text-muted-foreground">Owner: {job.owner_username}</p>
                    </div>
                    <span className="rounded-full bg-destructive/10 px-2 py-1 text-xs font-semibold text-destructive">
                      {friendlyStatus(job.status)}
                    </span>
                  </div>
                  {job.parser_warnings.length > 0 ? (
                    <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                      {job.parser_warnings.slice(0, 3).map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                  <p className="mt-3 text-xs text-muted-foreground">Updated {formatDate(job.updated_at)}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <AdminUserAnalyticsPanel />

      <AdminTextbookManagement />

      <AdminQualityTools />

      <AdminUserManagement />
    </div>
  );
}

function MetricCard({ metric }: { metric: CommandCenterMetric }) {
  const Icon = metricIcons[metric.key] ?? Database;
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{metric.label}</p>
          <p className="text-3xl font-semibold">{metric.value.toLocaleString()}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function friendlyStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatConfidence(value: number | null): string {
  return value === null ? "Confidence not recorded" : `${Math.round(value * 100)}% confidence`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
