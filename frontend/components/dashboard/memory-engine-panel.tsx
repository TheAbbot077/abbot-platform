"use client";

import { BrainCircuit, CheckCircle2, Dumbbell, Flame, Loader2, LockKeyhole, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { submitArielToExaminer, teachArielMemory } from "@/lib/api";
import { celebrate } from "@/lib/celebrations";
import type { TeachBackMemoryEngine } from "@/lib/types";

export type ArielTeachableConcept = {
  concept_id: number;
  concept_title: string;
  chapter_id: number;
  chapter_title: string;
  document_title: string;
  ariel_taught: boolean;
  examiner_unlocked: boolean;
};

export type ArielLearningConcept = ArielTeachableConcept & {
  learning_state: "ready" | "taught" | "locked";
};

export function MemoryEnginePanel({
  engine,
  subjectId,
  learningConcepts = [],
  onChanged
}: {
  engine?: TeachBackMemoryEngine;
  subjectId?: number;
  learningConcepts?: ArielLearningConcept[];
  onChanged: () => void;
}) {
  const [checkingConceptId, setCheckingConceptId] = useState<number | null>(null);
  const [teachingConceptId, setTeachingConceptId] = useState<number | null>(null);
  const [teachDrafts, setTeachDrafts] = useState<Record<number, string>>({});
  const [message, setMessage] = useState<string | null>(null);

  if ((!engine || engine.daily_rescue_missions.length === 0) && learningConcepts.length === 0) {
    return null;
  }

  const health = Number(engine?.memory_health.score ?? 100);
  const missionConceptIds = new Set(engine?.daily_rescue_missions.map((mission) => mission.concept_id) ?? []);
  const examinerUnlockedByConceptId = new Map(learningConcepts.map((concept) => [concept.concept_id, concept.examiner_unlocked]));
  const readyConcepts = learningConcepts.filter((concept) => concept.learning_state === "ready" && !missionConceptIds.has(concept.concept_id));
  const taughtConcepts = learningConcepts.filter((concept) => concept.learning_state === "taught" && !missionConceptIds.has(concept.concept_id));
  const lockedConcepts = learningConcepts.filter((concept) => concept.learning_state === "locked").slice(0, 8);

  async function handleExaminerCheck(conceptId: number) {
    setCheckingConceptId(conceptId);
    setMessage(null);
    try {
      const result = await submitArielToExaminer(conceptId, subjectId);
      if (result.passed) {
        celebrate(result.celebration ?? "ariel_examiner_passed");
        setMessage(`Ariel passed the examiner check with ${result.score}%.`);
      } else {
        setMessage(`Ariel scored ${result.score}%. Give it a quick refresher and try again.`);
      }
      onChanged();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not submit Ariel to the examiner.");
    } finally {
      setCheckingConceptId(null);
    }
  }

  async function handleTeachAriel(conceptId: number) {
    const taughtContent = teachDrafts[conceptId]?.trim();
    if (!taughtContent) {
      setMessage("Write a quick refresher lesson for Ariel first.");
      return;
    }

    setTeachingConceptId(conceptId);
    setMessage(null);
    try {
      await teachArielMemory(conceptId, taughtContent, subjectId);
      setTeachDrafts((currentDrafts) => ({ ...currentDrafts, [conceptId]: "" }));
      setMessage("Ariel saved your refresher lesson. Nice teach-back.");
      onChanged();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not teach Ariel right now.");
    } finally {
      setTeachingConceptId(null);
    }
  }

  return (
    <Card className="overflow-hidden border-secondary/50 bg-card/95 shadow-sm">
      <CardHeader className="gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
            <BrainCircuit className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <CardTitle>Ariel's memory gym</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">{engine?.headline ?? "Ariel is ready to learn what you've mastered."}</p>
            <p className="mt-2 text-xs font-medium text-primary">Ariel only knows what you teach.</p>
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Ariel's energy</span>
            <span className="font-medium">{engine?.memory_health.score ?? "100.00"}%</span>
          </div>
          <Progress value={health} />
          <p className="mt-2 text-xs text-muted-foreground">{engine?.memory_health.label ?? "Ariel is ready for its first lesson."}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <section>
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" aria-hidden="true" />
            <h3 className="text-sm font-semibold">Ready to teach</h3>
          </div>
          <div className="space-y-3">
            {message ? <p className="rounded-2xl border bg-background p-3 text-sm text-muted-foreground">{message}</p> : null}
            {engine?.daily_rescue_missions.map((mission) => (
              <div key={mission.id} className="rounded-2xl border bg-background/80 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold">{mission.mission_title ?? `Rescue mission: ${mission.concept_title}`}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {mission.friendly_message ?? "Give it a quick refresher lesson."}
                    </p>
                  </div>
                  <Badge tone="in_progress">{mission.priority} focus</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>{mission.recommended_action}</span>
                  <span>{mission.failed_bloom_level}</span>
                  <span>{mission.student_ai_score}% Ariel memory check</span>
                </div>
                <div className="mt-4 space-y-2">
                  <label className="block text-sm font-semibold" htmlFor={`teach-ariel-${mission.concept_id}`}>
                    Teach Ariel
                  </label>
                  <textarea
                    id={`teach-ariel-${mission.concept_id}`}
                    className="min-h-36 w-full resize-y rounded-2xl border bg-background px-3 py-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-ring"
                    value={teachDrafts[mission.concept_id] ?? ""}
                    onChange={(event) => setTeachDrafts((currentDrafts) => ({ ...currentDrafts, [mission.concept_id]: event.target.value }))}
                    placeholder="Explain this concept to Ariel in your own words. Use an example if you can."
                    disabled={teachingConceptId !== null || checkingConceptId !== null}
                  />
                </div>
                <div className="mt-3 grid gap-2 sm:flex sm:flex-wrap">
                  <Button
                    type="button"
                    size="sm"
                    className="w-full sm:w-auto"
                    onClick={() => handleTeachAriel(mission.concept_id)}
                    disabled={teachingConceptId !== null || checkingConceptId !== null || !teachDrafts[mission.concept_id]?.trim()}
                  >
                    {teachingConceptId === mission.concept_id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                    Save Ariel lesson
                  </Button>
                  {examinerUnlockedByConceptId.get(mission.concept_id) ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="w-full sm:w-auto"
                      onClick={() => handleExaminerCheck(mission.concept_id)}
                      disabled={checkingConceptId !== null}
                    >
                      {checkingConceptId === mission.concept_id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                      Submit Ariel to examiner
                    </Button>
                  ) : (
                    <p className="rounded-2xl bg-muted px-3 py-2 text-xs text-muted-foreground">
                      When the chapter is complete, Ariel can take the examiner challenge.
                    </p>
                  )}
                </div>
              </div>
            ))}
            {readyConcepts.length === 0 && (!engine || engine.daily_rescue_missions.length === 0) ? (
              <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">
                Pass a concept to give Ariel its next lesson.
              </p>
            ) : null}
            {readyConcepts.map((concept) => (
              <div key={concept.concept_id} className="rounded-2xl border bg-background/80 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold">{concept.concept_title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {concept.document_title} - {concept.chapter_title}
                    </p>
                  </div>
                  <Badge tone={concept.ariel_taught ? "passed" : "available"}>
                    Ready to teach
                  </Badge>
                </div>
                <div className="mt-4 space-y-2">
                  <label className="block text-sm font-semibold" htmlFor={`teach-ariel-${concept.concept_id}`}>
                    Teach Ariel
                  </label>
                  <textarea
                    id={`teach-ariel-${concept.concept_id}`}
                    className="min-h-36 w-full resize-y rounded-2xl border bg-background px-3 py-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-ring"
                    value={teachDrafts[concept.concept_id] ?? ""}
                    onChange={(event) => setTeachDrafts((currentDrafts) => ({ ...currentDrafts, [concept.concept_id]: event.target.value }))}
                    placeholder="Explain this concept to Ariel in your own words. Use an example if you can."
                    disabled={teachingConceptId !== null || checkingConceptId !== null}
                  />
                </div>
                <div className="mt-3 grid gap-2 sm:flex sm:flex-wrap">
                  <Button
                    type="button"
                    size="sm"
                    className="w-full sm:w-auto"
                    onClick={() => handleTeachAriel(concept.concept_id)}
                    disabled={teachingConceptId !== null || checkingConceptId !== null || !teachDrafts[concept.concept_id]?.trim()}
                  >
                    {teachingConceptId === concept.concept_id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                    Save Ariel lesson
                  </Button>
                  {concept.examiner_unlocked ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="w-full sm:w-auto"
                      onClick={() => handleExaminerCheck(concept.concept_id)}
                      disabled={checkingConceptId !== null}
                    >
                      {checkingConceptId === concept.concept_id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                      Submit Ariel to examiner
                    </Button>
                  ) : (
                    <p className="rounded-2xl bg-muted px-3 py-2 text-xs text-muted-foreground">
                      When the chapter is complete, Ariel can take the examiner challenge.
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden="true" />
            <h3 className="text-sm font-semibold">Already taught</h3>
          </div>
          <div className="space-y-3">
            {taughtConcepts.length > 0 ? taughtConcepts.map((concept) => (
              <div key={concept.concept_id} className="rounded-2xl border bg-background/80 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold">{concept.concept_title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {concept.document_title} - {concept.chapter_title}
                    </p>
                  </div>
                  <Badge tone="passed">Ariel learned it</Badge>
                </div>
                <details className="mt-3 rounded-2xl bg-muted/70 p-3 text-sm text-muted-foreground">
                  <summary className="cursor-pointer font-medium text-foreground">Review what Ariel learned</summary>
                  <p className="mt-2">
                    Ariel has a saved lesson for this concept. Reteach it anytime with a clearer example if you want to strengthen its memory.
                  </p>
                </details>
                <div className="mt-4 space-y-2">
                  <label className="block text-sm font-semibold" htmlFor={`reteach-ariel-${concept.concept_id}`}>
                    Reteach Ariel if needed
                  </label>
                  <textarea
                    id={`reteach-ariel-${concept.concept_id}`}
                    className="min-h-28 w-full resize-y rounded-2xl border bg-background px-3 py-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-ring"
                    value={teachDrafts[concept.concept_id] ?? ""}
                    onChange={(event) => setTeachDrafts((currentDrafts) => ({ ...currentDrafts, [concept.concept_id]: event.target.value }))}
                    placeholder="Add a stronger explanation, a new example, or a simpler version for Ariel."
                    disabled={teachingConceptId !== null || checkingConceptId !== null}
                  />
                </div>
                <div className="mt-3 grid gap-2 sm:flex sm:flex-wrap">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="w-full sm:w-auto"
                    onClick={() => handleTeachAriel(concept.concept_id)}
                    disabled={teachingConceptId !== null || checkingConceptId !== null || !teachDrafts[concept.concept_id]?.trim()}
                  >
                    {teachingConceptId === concept.concept_id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RotateCcw className="h-4 w-4" aria-hidden="true" />}
                    Reteach Ariel
                  </Button>
                  {concept.examiner_unlocked ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="w-full sm:w-auto"
                      onClick={() => handleExaminerCheck(concept.concept_id)}
                      disabled={checkingConceptId !== null}
                    >
                      {checkingConceptId === concept.concept_id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                      Submit Ariel to examiner
                    </Button>
                  ) : (
                    <p className="rounded-2xl bg-muted px-3 py-2 text-xs text-muted-foreground">
                      Finish this chapter to submit Ariel to the examiner.
                    </p>
                  )}
                </div>
              </div>
            )) : (
              <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">
                Ariel has not learned a concept in this subject yet.
              </p>
            )}
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center gap-2">
            <LockKeyhole className="h-4 w-4 text-primary" aria-hidden="true" />
            <h3 className="text-sm font-semibold">Locked until mastered</h3>
          </div>
          {lockedConcepts.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {lockedConcepts.map((concept) => (
                <div key={concept.concept_id} className="rounded-2xl border bg-muted/60 p-3 text-sm">
                  <p className="font-medium">{concept.concept_title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Pass this concept before Ariel can learn it.</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">
              No locked concepts in this subject workspace right now.
            </p>
          )}
        </section>

        {engine ? <section className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border p-4">
            <div className="mb-2 flex items-center gap-2">
              <Flame className="h-4 w-4 text-primary" aria-hidden="true" />
              <h3 className="text-sm font-semibold">Rescue streak</h3>
            </div>
            <p className="text-2xl font-semibold">{engine.reinforcement_streak.count}</p>
            <p className="mt-1 text-xs text-muted-foreground">{engine.reinforcement_streak.label}</p>
          </div>
          <div className="rounded-2xl border p-4 md:col-span-2">
            <div className="mb-2 flex items-center gap-2">
              <Dumbbell className="h-4 w-4 text-primary" aria-hidden="true" />
              <h3 className="text-sm font-semibold">{engine.teach_back_challenge.title}</h3>
            </div>
            <p className="text-sm text-muted-foreground">{engine.teach_back_challenge.prompt}</p>
          </div>
        </section> : null}

        {engine && engine.bloom_mastery_badges.length > 0 ? (
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
              <h3 className="text-sm font-semibold">Skill badges</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {engine.bloom_mastery_badges.map((badge) => (
                <Badge key={badge.bloom_level} tone="available">{badge.label}</Badge>
              ))}
            </div>
          </section>
        ) : null}
      </CardContent>
    </Card>
  );
}
