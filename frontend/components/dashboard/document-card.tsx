"use client";

import Link from "next/link";
import { ArrowRight, FileText, RefreshCw, Trash2 } from "lucide-react";

import { ChapterSection } from "@/components/dashboard/chapter-section";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { deleteDocument, restartDocument } from "@/lib/api";
import type { DashboardDocument } from "@/lib/types";

const statusLabels: Record<string, string> = {
  uploaded: "Preparing your textbook",
  extracting_text: "Reading your textbook",
  chapters_detected: "Organizing your chapters",
  processing_concepts: "Finding what you need to learn",
  ready: "Ready to study",
  failed: "Needs a quick retry"
};

export function DocumentCard({ document, onChanged }: { document: DashboardDocument; onChanged: () => void }) {
  const completion = Number(document.completion_percentage);
  const canContinue = ["start_current_concept", "continue_current_concept"].includes(document.current_recommended_next_action);
  const isWaitingForConcepts = document.current_recommended_next_action === "wait_for_concepts";
  const conceptsAreMissing = document.current_recommended_next_action === "concepts_missing";

  async function handleRestartDocument() {
    const confirmed = window.confirm("Restart this textbook? This clears progress, attempts, lessons, and reinforcement data, but keeps the uploaded PDF and chapter/concept order.");
    if (!confirmed) {
      return;
    }

    await restartDocument(document.document_id);
    onChanged();
  }

  async function handleDeleteDocument() {
    const confirmed = window.confirm("Delete this textbook? This removes the uploaded PDF, chapters, concepts, progress, quiz attempts, and Ariel memory for this textbook.");
    if (!confirmed) {
      return;
    }

    await deleteDocument(document.document_id);
    onChanged();
  }

  return (
    <Card className="overflow-hidden bg-card/95 shadow-sm">
      <CardHeader className="gap-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
              <FileText className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <CardTitle className="truncate">{document.title}</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">{statusLabels[document.status] ?? document.status.replaceAll("_", " ")}</p>
            </div>
          </div>
          <div className="grid gap-2 sm:flex sm:flex-wrap">
            {canContinue ? (
              <Button asChild className="w-full sm:w-auto">
                <Link href={`/learn/${document.document_id}${document.subject_id ? `?subject=${document.subject_id}` : ""}`}>
                  Continue
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <Button className="w-full sm:w-auto" disabled>
                {isWaitingForConcepts ? "Preparing lessons" : conceptsAreMissing ? "Needs retry" : "Finished"}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            )}
            <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={handleRestartDocument}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Fresh start
            </Button>
            <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={handleDeleteDocument}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Remove
            </Button>
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Textbook journey</span>
            <span className="font-medium">{document.completion_percentage}%</span>
          </div>
          <Progress value={completion} />
        </div>
      </CardHeader>
      <CardContent>
        {document.chapters.length > 0 ? (
          document.chapters.map((chapter) => <ChapterSection key={chapter.chapter_id} chapter={chapter} onChanged={onChanged} />)
        ) : isWaitingForConcepts ? (
          <p className="rounded-2xl bg-muted/70 p-4 text-sm text-muted-foreground">The Abbot found the textbook and is still finding the lessons inside it. Check again shortly.</p>
        ) : conceptsAreMissing ? (
          <p className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">This textbook has chapters but no lessons yet. Run missing concept extraction or reprocess the textbook.</p>
        ) : (
          <p className="rounded-2xl bg-muted/70 p-4 text-sm text-muted-foreground">Preparing your textbook. Chapters will appear here soon.</p>
        )}
      </CardContent>
    </Card>
  );
}
