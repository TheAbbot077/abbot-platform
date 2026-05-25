"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, RefreshCw, Search, Sparkles } from "lucide-react";

import {
  getAdminConceptQuality,
  regenerateAdminConceptMcqs,
  regenerateAdminConceptTutor,
} from "@/lib/api";
import type { AdminConceptQuality, AdminConceptQualityResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type IssueFilter = "all" | "failed" | "objective";

export function AdminQualityTools() {
  const [quality, setQuality] = useState<AdminConceptQualityResponse | null>(null);
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [chapterId, setChapterId] = useState("");
  const [issueFilter, setIssueFilter] = useState<IssueFilter>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [busyConceptId, setBusyConceptId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadQualityTools() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getAdminConceptQuality({
        q: query,
        documentId,
        chapterId,
        issue: issueFilter,
      });
      setQuality(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load concept quality tools.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadQualityTools();
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query, documentId, chapterId, issueFilter]);

  async function refreshMcqs(concept: AdminConceptQuality) {
    if (!window.confirm(`Refresh unanswered MCQs for "${concept.title}"? Answered questions, attempts, and progress stay untouched.`)) {
      return;
    }
    setBusyConceptId(concept.id);
    setMessage(null);
    setError(null);
    try {
      const response = await regenerateAdminConceptMcqs(concept.id);
      setMessage(`${response.detail} Cleared: ${response.deleted_count}.`);
      await loadQualityTools();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to refresh MCQs.");
    } finally {
      setBusyConceptId(null);
    }
  }

  async function refreshTutor(concept: AdminConceptQuality) {
    if (!window.confirm(`Refresh stored The Abbot lesson for "${concept.title}"? Student progress stays untouched.`)) {
      return;
    }
    setBusyConceptId(concept.id);
    setMessage(null);
    setError(null);
    try {
      const response = await regenerateAdminConceptTutor(concept.id);
      setMessage(`${response.detail} Cleared: ${response.deleted_count}.`);
      await loadQualityTools();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to refresh The Abbot lesson.");
    } finally {
      setBusyConceptId(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Quiz, tutor, and concept quality</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Review concept health, MCQ outcomes, possible objective extraction mistakes, and safe regeneration tools.
            </p>
          </div>
          <div className="text-sm text-muted-foreground">{quality?.total_count.toLocaleString() ?? 0} concepts found</div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 xl:grid-cols-[1fr_150px_150px_180px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              className="h-11 w-full rounded-xl border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search concepts, chapters, or textbooks"
            />
          </label>
          <input
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={documentId}
            onChange={(event) => setDocumentId(event.target.value.replace(/\D/g, ""))}
            placeholder="Textbook ID"
          />
          <input
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={chapterId}
            onChange={(event) => setChapterId(event.target.value.replace(/\D/g, ""))}
            placeholder="Chapter ID"
          />
          <select
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={issueFilter}
            onChange={(event) => setIssueFilter(event.target.value as IssueFilter)}
          >
            <option value="all">All concepts</option>
            <option value="failed">Commonly failed</option>
            <option value="objective">Possible objectives</option>
          </select>
        </div>

        {error ? <p className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p> : null}
        {message ? <p className="rounded-xl border bg-muted/40 p-3 text-sm text-muted-foreground">{message}</p> : null}

        <div className="grid gap-5 2xl:grid-cols-[1fr_360px]">
          <ConceptQualityTable
            concepts={quality?.concepts ?? []}
            isLoading={isLoading}
            busyConceptId={busyConceptId}
            onRefreshMcqs={refreshMcqs}
            onRefreshTutor={refreshTutor}
          />
          <QualitySidePanel quality={quality} />
        </div>
      </CardContent>
    </Card>
  );
}

function ConceptQualityTable({
  concepts,
  isLoading,
  busyConceptId,
  onRefreshMcqs,
  onRefreshTutor,
}: {
  concepts: AdminConceptQuality[];
  isLoading: boolean;
  busyConceptId: number | null;
  onRefreshMcqs: (concept: AdminConceptQuality) => void;
  onRefreshTutor: (concept: AdminConceptQuality) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-3 font-semibold">Concept</th>
            <th className="px-3 py-3 font-semibold">Textbook</th>
            <th className="px-3 py-3 font-semibold">MCQs</th>
            <th className="px-3 py-3 font-semibold">Pass rate</th>
            <th className="px-3 py-3 font-semibold">Lessons</th>
            <th className="px-3 py-3 font-semibold">Quality notes</th>
            <th className="px-3 py-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td className="px-3 py-6 text-muted-foreground" colSpan={7}>
                <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
                Loading quality tools...
              </td>
            </tr>
          ) : concepts.length === 0 ? (
            <tr>
              <td className="px-3 py-6 text-muted-foreground" colSpan={7}>No concepts match these filters.</td>
            </tr>
          ) : (
            concepts.map((concept) => (
              <tr key={concept.id} className="border-t">
                <td className="px-3 py-3">
                  <p className="font-medium">{concept.chapter_sequence_number}.{concept.sequence_number} {concept.title}</p>
                  <p className="text-xs text-muted-foreground">Chapter: {concept.chapter_title}</p>
                </td>
                <td className="px-3 py-3">
                  <p>{concept.document_title}</p>
                  <p className="text-xs text-muted-foreground">Owner: {concept.owner_username}</p>
                </td>
                <td className="px-3 py-3">
                  <p>{concept.question_count} total</p>
                  <p className="text-xs text-muted-foreground">{concept.unanswered_question_count} ready to reuse</p>
                </td>
                <td className="px-3 py-3">
                  <p>{concept.pass_rate === null ? "No attempts" : `${concept.pass_rate}%`}</p>
                  <p className="text-xs text-muted-foreground">{concept.pass_count} pass / {concept.fail_count} fail</p>
                </td>
                <td className="px-3 py-3">
                  <p>{concept.lesson_count} lessons</p>
                  <p className="text-xs text-muted-foreground">{concept.tutor_message_count} follow-ups</p>
                </td>
                <td className="px-3 py-3">
                  {concept.possible_objective_match ? (
                    <div className="rounded-lg border border-amber-300/60 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                      Possible objective: {concept.matched_objective}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">No objective warning</span>
                  )}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" size="sm" variant="outline" onClick={() => onRefreshMcqs(concept)} disabled={busyConceptId === concept.id}>
                      <RefreshCw className="h-4 w-4" aria-hidden="true" />
                      MCQs
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => onRefreshTutor(concept)} disabled={busyConceptId === concept.id}>
                      <Sparkles className="h-4 w-4" aria-hidden="true" />
                      The Abbot
                    </Button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function QualitySidePanel({ quality }: { quality: AdminConceptQualityResponse | null }) {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border bg-background p-4">
        <h3 className="text-sm font-semibold">Commonly failed concepts</h3>
        {!quality || quality.commonly_failed_concepts.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">No failed concept patterns yet.</p>
        ) : (
          <div className="mt-3 space-y-3">
            {quality.commonly_failed_concepts.map((concept) => (
              <div key={concept.id} className="rounded-lg bg-muted/40 p-3 text-sm">
                <p className="font-medium">{concept.title}</p>
                <p className="text-xs text-muted-foreground">{concept.document_title} - {concept.chapter_title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {concept.fail_count} failed attempts - {concept.pass_rate === null ? "no pass rate" : `${concept.pass_rate}% pass rate`}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border bg-background p-4">
        <div className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <div>
            <h3 className="text-sm font-semibold">Flagged questions</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {quality?.flagged_questions.message ?? "Question flagging is not enabled yet."}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
