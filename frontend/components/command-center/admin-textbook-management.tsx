"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, BookOpenCheck, Loader2, RefreshCw, Search, Trash2 } from "lucide-react";

import {
  deleteAdminTextbook,
  getAdminTextbookDetail,
  getAdminTextbookParserPreview,
  getAdminTextbooks,
  reprocessAdminTextbook,
} from "@/lib/api";
import type { AdminParserPreview, AdminTextbook, AdminTextbookDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type StatusFilter = "all" | "uploaded" | "extracting_text" | "chapters_detected" | "processing_concepts" | "ready" | "failed";
type ConfidenceFilter = "all" | "low" | "high" | "unknown";

export function AdminTextbookManagement() {
  const [textbooks, setTextbooks] = useState<AdminTextbook[]>([]);
  const [selectedTextbook, setSelectedTextbook] = useState<AdminTextbookDetail | null>(null);
  const [preview, setPreview] = useState<AdminParserPreview | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [confidenceFilter, setConfidenceFilter] = useState<ConfidenceFilter>("all");
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadTextbooks() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getAdminTextbooks({ q: query, status: statusFilter, confidence: confidenceFilter });
      setTextbooks(response.textbooks);
      setTotalCount(response.total_count);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load textbooks.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadTextbooks();
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query, statusFilter, confidenceFilter]);

  async function selectTextbook(documentId: number) {
    setPreview(null);
    setMessage(null);
    setError(null);
    try {
      setSelectedTextbook(await getAdminTextbookDetail(documentId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load textbook.");
    }
  }

  async function runPreview() {
    if (!selectedTextbook) {
      return;
    }
    setIsBusy(true);
    setMessage(null);
    setError(null);
    try {
      setPreview(await getAdminTextbookParserPreview(selectedTextbook.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to run parser preview.");
    } finally {
      setIsBusy(false);
    }
  }

  async function reprocessTextbook() {
    if (!selectedTextbook) {
      return;
    }
    const warning = selectedTextbook.progress_exists
      ? "This textbook has learning progress. Reprocessing may reset chapters, concepts, quizzes, lessons, Ariel memory, and recommendations. Continue?"
      : "Reprocess this textbook? Existing chapters and concepts will be replaced.";
    if (!window.confirm(warning)) {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const response = await reprocessAdminTextbook(selectedTextbook.id, selectedTextbook.progress_exists);
      setMessage(response.detail);
      await loadTextbooks();
      setSelectedTextbook(await getAdminTextbookDetail(selectedTextbook.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to queue reprocessing.");
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteTextbook() {
    if (!selectedTextbook) {
      return;
    }
    if (!window.confirm(`Delete "${selectedTextbook.title}"? This cascades chapters, concepts, progress, quizzes, and the stored file.`)) {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      await deleteAdminTextbook(selectedTextbook.id);
      setMessage("Textbook deleted.");
      setSelectedTextbook(null);
      setPreview(null);
      await loadTextbooks();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to delete textbook.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Textbook and parser management</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Inspect uploads, parser confidence, warnings, ordered chapters, and safe reprocessing.</p>
          </div>
          <div className="text-sm text-muted-foreground">{totalCount.toLocaleString()} textbooks found</div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 lg:grid-cols-[1fr_190px_190px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              className="h-11 w-full rounded-xl border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search title or owner"
            />
          </label>
          <select className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
            <option value="all">All statuses</option>
            <option value="uploaded">Uploaded</option>
            <option value="extracting_text">Preparing text</option>
            <option value="chapters_detected">Chapters found</option>
            <option value="processing_concepts">Finding concepts</option>
            <option value="ready">Ready</option>
            <option value="failed">Failed</option>
          </select>
          <select className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" value={confidenceFilter} onChange={(event) => setConfidenceFilter(event.target.value as ConfidenceFilter)}>
            <option value="all">All confidence</option>
            <option value="low">Low confidence</option>
            <option value="high">Good confidence</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>

        {error ? <p className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p> : null}
        {message ? <p className="rounded-xl border bg-muted/40 p-3 text-sm text-muted-foreground">{message}</p> : null}

        <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <TextbookTable textbooks={textbooks} isLoading={isLoading} selectedId={selectedTextbook?.id ?? null} onSelect={selectTextbook} />
          <TextbookDetailPanel textbook={selectedTextbook} preview={preview} isBusy={isBusy} onPreview={runPreview} onReprocess={reprocessTextbook} onDelete={deleteTextbook} />
        </div>
      </CardContent>
    </Card>
  );
}

function TextbookTable({ textbooks, isLoading, selectedId, onSelect }: { textbooks: AdminTextbook[]; isLoading: boolean; selectedId: number | null; onSelect: (id: number) => void }) {
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-3 font-semibold">Textbook</th>
            <th className="px-3 py-3 font-semibold">Owner</th>
            <th className="px-3 py-3 font-semibold">Status</th>
            <th className="px-3 py-3 font-semibold">Confidence</th>
            <th className="px-3 py-3 font-semibold">Chapters</th>
            <th className="px-3 py-3 font-semibold">Warnings</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td className="px-3 py-6 text-muted-foreground" colSpan={6}>
                <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
                Loading textbooks...
              </td>
            </tr>
          ) : textbooks.length === 0 ? (
            <tr>
              <td className="px-3 py-6 text-muted-foreground" colSpan={6}>No textbooks match these filters.</td>
            </tr>
          ) : (
            textbooks.map((textbook) => (
              <tr key={textbook.id} className={`cursor-pointer border-t hover:bg-muted/50 ${selectedId === textbook.id ? "bg-muted/60" : ""}`} onClick={() => onSelect(textbook.id)}>
                <td className="px-3 py-3">
                  <p className="font-medium">{textbook.title}</p>
                  <p className="text-xs text-muted-foreground">{textbook.subject_name ?? "No subject"}</p>
                </td>
                <td className="px-3 py-3">{textbook.owner_username}</td>
                <td className="px-3 py-3">{friendlyStatus(textbook.status)}</td>
                <td className="px-3 py-3">{formatConfidence(textbook.parser_confidence_score)}</td>
                <td className="px-3 py-3">{textbook.chapter_count}</td>
                <td className="px-3 py-3">{textbook.parser_warnings.length}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function TextbookDetailPanel({ textbook, preview, isBusy, onPreview, onReprocess, onDelete }: { textbook: AdminTextbookDetail | null; preview: AdminParserPreview | null; isBusy: boolean; onPreview: () => void; onReprocess: () => void; onDelete: () => void }) {
  if (!textbook) {
    return <div className="rounded-xl border bg-background p-5 text-sm text-muted-foreground">Select a textbook to inspect parser details and chapter order.</div>;
  }

  return (
    <div className="space-y-4 rounded-xl border bg-background p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-lg font-semibold">{textbook.title}</p>
          <p className="text-sm text-muted-foreground">{textbook.owner_username} - {textbook.subject_name ?? "No subject"}</p>
          <p className="mt-1 text-xs text-muted-foreground">{friendlyStatus(textbook.status)} - {formatConfidence(textbook.parser_confidence_score)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={onPreview} disabled={isBusy}>
            <BookOpenCheck className="h-4 w-4" aria-hidden="true" />
            Preview
          </Button>
          <Button type="button" variant="outline" onClick={onReprocess} disabled={isBusy}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Reprocess
          </Button>
          <Button type="button" variant="outline" onClick={onDelete} disabled={isBusy}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Delete
          </Button>
        </div>
      </div>

      {textbook.progress_exists ? (
        <div className="flex gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          This textbook has learning progress. Reprocessing may reset progress-related records.
        </div>
      ) : null}

      <section>
        <h3 className="text-sm font-semibold">Parser warnings</h3>
        {textbook.parser_warnings.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">No parser warnings recorded.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {textbook.parser_warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        )}
      </section>

      <section>
        <h3 className="text-sm font-semibold">Stored chapters in order</h3>
        <div className="mt-2 max-h-52 overflow-auto rounded-lg border">
          {textbook.chapters.map((chapter) => (
            <div key={chapter.id} className="border-b px-3 py-2 text-sm last:border-b-0">
              <span className="font-semibold">{chapter.sequence_number}. </span>
              {chapter.title}
              <span className="ml-2 text-xs text-muted-foreground">{chapter.concept_count} concepts</span>
            </div>
          ))}
        </div>
      </section>

      {preview ? <ParserPreview preview={preview} /> : null}
    </div>
  );
}

function ParserPreview({ preview }: { preview: AdminParserPreview }) {
  return (
    <section className="space-y-3">
      <h3 className="text-sm font-semibold">Parser dry preview</h3>
      <div className="grid gap-2 sm:grid-cols-2">
        <MiniStat label="Legacy proposal" value={preview.legacy.accepted_chapter_count} />
        <MiniStat label="Resolver proposal" value={preview.resolver.accepted_chapter_count} />
      </div>
      {preview.differences.length > 0 ? (
        <div className="rounded-lg bg-muted/40 p-3">
          <p className="text-xs font-semibold">Differences</p>
          <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
            {preview.differences.slice(0, 5).map((difference) => <li key={difference}>{difference}</li>)}
          </ul>
        </div>
      ) : null}
      <div className="max-h-48 overflow-auto rounded-lg border">
        {preview.legacy.accepted_chapters.slice(0, 10).map((chapter) => (
          <div key={`${chapter.sequence_number}-${chapter.title}`} className="border-b px-3 py-2 text-sm last:border-b-0">
            <span className="font-semibold">{chapter.sequence_number}. </span>
            {chapter.title}
            <p className="text-xs text-muted-foreground">{chapter.preview}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value.toLocaleString()}</p>
    </div>
  );
}

function friendlyStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatConfidence(value: number | null): string {
  return value === null ? "unknown" : `${Math.round(value * 100)}%`;
}
