"use client";

import { RefreshCw } from "lucide-react";

import { ConceptRow } from "@/components/dashboard/concept-row";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { restartChapter } from "@/lib/api";
import type { DashboardChapter } from "@/lib/types";

export function ChapterSection({ chapter, onChanged }: { chapter: DashboardChapter; onChanged: () => void }) {
  const completion = Number(chapter.completion_percentage);

  async function handleRestartChapter() {
    const confirmed = window.confirm("Restart this chapter? This clears progress, attempts, and lessons for every concept in the chapter while keeping the original order.");
    if (!confirmed) {
      return;
    }

    await restartChapter(chapter.chapter_id);
    onChanged();
  }

  return (
    <section className="border-t py-5 first:border-t-0">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold">
            Chapter {chapter.sequence_number}: {chapter.title}
          </h3>
          <p className="text-xs text-muted-foreground">{chapter.concepts.length} bite-sized lessons</p>
        </div>
        <div className="flex w-full flex-col gap-3 sm:w-64">
          <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>Chapter vibe</span>
            <span>{chapter.completion_percentage}%</span>
          </div>
          <Progress value={completion} />
          <Button type="button" variant="outline" size="sm" className="w-full" onClick={handleRestartChapter}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Replay chapter
          </Button>
        </div>
      </div>
      <div>
        {chapter.concepts.map((concept) => (
          <ConceptRow key={concept.concept_id} concept={concept} />
        ))}
      </div>
    </section>
  );
}
