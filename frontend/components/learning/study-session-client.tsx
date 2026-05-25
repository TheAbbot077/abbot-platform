"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { BookOpen, CheckCircle2, Drama, Feather, Loader2, MessageSquare, Quote, RotateCcw, Send, Sparkles, Users } from "lucide-react";

import { askTutorQuestion, getCurrentConcept, getCurrentMcqs, requestTutorLesson, restartCurrentConcept, submitCurrentMcqs } from "@/lib/api";
import type {
  CurrentConcept,
  MCQResponse,
  QuizAnswers,
  QuizOptionKey,
  QuizSubmissionResult,
  TutorAnswer,
  TutorLesson
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MathMarkdown } from "@/components/learning/math-markdown";
import { StudyToolsButton } from "@/components/study-toolkit";
import { VisualRenderer } from "@/components/learning/visual-renderer";
import { celebrate } from "@/lib/celebrations";

type LoadingState = "idle" | "concept" | "tutor" | "ask" | "mcq" | "submit";

const optionKeys: QuizOptionKey[] = ["A", "B", "C", "D"];

const sourceModeLabels: Record<TutorAnswer["source_mode"], string> = {
  document_only: "From your material",
  document_plus_general_knowledge: "The Abbot used your material plus clarification",
  general_knowledge_clarification: "The Abbot clarified using general knowledge"
};

type LiteratureCard = {
  title: string;
  icon: typeof BookOpen;
  content: string[];
};

function isTutorLesson(value: unknown): value is TutorLesson {
  return Boolean(value && typeof value === "object" && "concept_id" in value && "explanation" in value);
}

export function StudySessionClient({ documentId, subjectId }: { documentId: string; subjectId?: number }) {
  const [concept, setConcept] = useState<CurrentConcept | null>(null);
  const [lesson, setLesson] = useState<TutorLesson | null>(null);
  const [followUps, setFollowUps] = useState<TutorAnswer[]>([]);
  const [question, setQuestion] = useState("");
  const [mcqs, setMcqs] = useState<MCQResponse["questions"]>([]);
  const [answers, setAnswers] = useState<QuizAnswers>({});
  const [result, setResult] = useState<QuizSubmissionResult | null>(null);
  const [loading, setLoading] = useState<LoadingState>("concept");
  const [error, setError] = useState<string | null>(null);
  const followUpInputRef = useRef<HTMLTextAreaElement | null>(null);

  async function loadCurrentConcept() {
    setLoading("concept");
    setError(null);
    try {
      const response = await getCurrentConcept(documentId, subjectId);
      setConcept(response.current_concept);
      setLesson(null);
      setFollowUps([]);
      setQuestion("");
      setMcqs([]);
      setAnswers({});
      setResult(null);
    } catch (caught) {
      setError(caught instanceof Error ? friendlyError(caught.message) : "The Abbot needs a moment.");
    } finally {
      setLoading("idle");
    }
  }

  useEffect(() => {
    void loadCurrentConcept();
  }, [documentId, subjectId]);

  const answeredQuestionCount = useMemo(
    () => mcqs.filter((question) => answers[String(question.id)]?.trim()).length,
    [answers, mcqs]
  );

  async function handleTeachConcept() {
    setLoading("tutor");
    setError(null);
    try {
      const response = await requestTutorLesson(documentId, subjectId);
      if (isTutorLesson(response)) {
        setLesson(response);
      } else {
        setError("There is no unlocked concept ready for The Abbot yet.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? friendlyError(caught.message) : "The Abbot needs a moment.");
    } finally {
      setLoading("idle");
    }
  }

  async function handleLoadMcqs() {
    setLoading("mcq");
    setError(null);
    try {
      const response = await getCurrentMcqs(documentId);
      setMcqs(response.questions);
      setResult(null);
    } catch (caught) {
      setError(caught instanceof Error ? friendlyError(caught.message) : "The practice questions need a moment.");
    } finally {
      setLoading("idle");
    }
  }

  async function handleAskForClarification() {
    if (!lesson) {
      await handleTeachConcept();
    }
    setQuestion("Can you explain this concept again in a simpler way?");
    window.setTimeout(() => {
      followUpInputRef.current?.focus();
      followUpInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
  }

  async function handleRetryQuiz() {
    setAnswers({});
    setResult(null);
    await handleLoadMcqs();
  }

  async function handleAskTutor() {
    if (!concept || !question.trim()) {
      return;
    }

    setLoading("ask");
    setError(null);
    try {
      const response = await askTutorQuestion(concept.concept_id, question.trim(), subjectId);
      setFollowUps((currentFollowUps) => [...currentFollowUps, response]);
      setQuestion("");
    } catch (caught) {
      setError(caught instanceof Error ? friendlyError(caught.message) : "The Abbot needs a moment.");
    } finally {
      setLoading("idle");
    }
  }

  async function handleSubmitAnswers() {
    setLoading("submit");
    setError(null);
    try {
      const response = await submitCurrentMcqs(documentId, answers);
      setResult(response);
      if (response.passed) {
        celebrate(response.celebration ?? "concept_passed");
      }
    } catch (caught) {
      setError(caught instanceof Error ? friendlyError(caught.message) : "Your answers need a moment.");
    } finally {
      setLoading("idle");
    }
  }

  async function handleRestartConcept() {
    const confirmed = window.confirm("Restart this concept lesson? This clears attempts, The Abbot lesson, follow-up questions, and practice questions for the current concept.");
    if (!confirmed) {
      return;
    }

    setLoading("concept");
    setError(null);
    try {
      await restartCurrentConcept(documentId);
      await loadCurrentConcept();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not restart this concept.");
    } finally {
      setLoading("idle");
    }
  }

  function setAnswer(questionId: number, answer: string) {
    setAnswers((currentAnswers) => ({
      ...currentAnswers,
      [String(questionId)]: answer
    }));
  }

  function friendlyError(message: string): string {
    if (message.toLowerCase().includes("openai") || message.toLowerCase().includes("endpoint") || message.toLowerCase().includes("status 5")) {
      return "The Abbot needs a moment. Try again in a little bit.";
    }
    return message;
  }

  if (loading === "concept" && !concept) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading your next concept...
        </CardContent>
      </Card>
    );
  }

  if (!concept) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Nothing to study right now</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>There is no unlocked concept for this document. The document may still be processing, or all required concepts may already be complete.</p>
          <Button type="button" variant="outline" onClick={loadCurrentConcept}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Check again
          </Button>
          {error ? <p className="text-destructive">{error}</p> : null}
        </CardContent>
      </Card>
    );
  }

  const isBusy = loading !== "idle";
  const canSubmit = mcqs.length > 0 && answeredQuestionCount === mcqs.length && !isBusy;
  const literatureCards = lesson?.is_literary ? buildLiteratureCards(lesson) : [];
  const tutorHeader = concept.subject_name ? `The Abbot - ${concept.subject_name}` : "The Abbot";

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-2">
              <CardTitle className="text-2xl">{concept.title}</CardTitle>
              <p className="text-sm text-muted-foreground">
                Chapter {concept.chapter_sequence_number}
                {concept.chapter_title ? `: ${concept.chapter_title}` : ""} - Concept {concept.sequence_number}
              </p>
            </div>
            <Badge tone={concept.status}>{concept.status.replace("_", " ")}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 sm:flex sm:flex-wrap">
          <Button type="button" className="w-full sm:w-auto" onClick={handleTeachConcept} disabled={isBusy}>
            {loading === "tutor" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <BookOpen className="h-4 w-4" aria-hidden="true" />}
            Learn with The Abbot
          </Button>
          <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={handleLoadMcqs} disabled={isBusy || !lesson}>
            {loading === "mcq" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Sparkles className="h-4 w-4" aria-hidden="true" />}
            Practice questions
          </Button>
          {result?.passed ? (
            <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={loadCurrentConcept} disabled={isBusy}>
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Continue to next concept
            </Button>
          ) : null}
          <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={handleRestartConcept} disabled={isBusy}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Restart concept
          </Button>
          <StudyToolsButton scope={`concept_${concept.concept_id}`} className="w-full sm:w-auto" />
        </CardContent>
      </Card>

      {error ? (
        <Card className="border-destructive/40">
          <CardContent className="p-5 text-sm text-destructive">{error}</CardContent>
        </Card>
      ) : null}

      {lesson ? (
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>{tutorHeader}</CardTitle>
            <p className="text-sm text-muted-foreground">Focused on this subject and concept only.</p>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-3xl border bg-background/80 p-4 shadow-sm sm:p-5">
              <div className="mb-3 flex items-center gap-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <BookOpen className="h-4 w-4" aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-sm font-semibold">Lesson from The Abbot</h3>
                  <p className="text-xs text-muted-foreground">One concept, clearly explained.</p>
                </div>
              </div>
              <MathMarkdown className="text-[0.95rem] leading-7 sm:text-sm sm:leading-6">{lesson.explanation}</MathMarkdown>
            </div>
            {lesson.visual_content ? <VisualRenderer visualContent={lesson.visual_content} /> : null}
            {literatureCards.length > 0 ? <LiteratureLessonCards cards={literatureCards} /> : null}
            {lesson.examples.length > 0 ? (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold">Examples</h4>
                <ul className="space-y-2">
                  {lesson.examples.map((example, index) => (
                    <li key={`${example}-${index}`} className="rounded-2xl border bg-background p-4">
                      <MathMarkdown muted>{example}</MathMarkdown>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <p className="text-sm font-medium text-primary">{lesson.next_action}</p>

            <div className="sticky bottom-[calc(6.75rem+env(safe-area-inset-bottom))] z-20 -mx-2 space-y-3 rounded-3xl border bg-card/95 p-3 shadow-lg shadow-primary/10 backdrop-blur sm:static sm:mx-0 sm:border-t sm:bg-transparent sm:p-0 sm:pt-5 sm:shadow-none">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-primary" aria-hidden="true" />
                <h4 className="text-sm font-semibold">Ask a follow-up</h4>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <textarea
                  ref={followUpInputRef}
                  className="min-h-24 flex-1 resize-y rounded-2xl border bg-background px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-ring sm:min-h-11"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask The Abbot about this concept"
                  disabled={isBusy}
                />
                <Button type="button" className="w-full sm:w-auto" onClick={handleAskTutor} disabled={isBusy || !question.trim()}>
                  {loading === "ask" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
                  Ask The Abbot
                </Button>
              </div>
              {followUps.length > 0 ? (
                <div className="space-y-3">
                  {followUps.map((followUp, index) => (
                    <div key={`${followUp.student_question}-${index}`} className="space-y-2 rounded-2xl border bg-background p-4 text-sm">
                      <p className="font-medium">{followUp.student_question}</p>
                      <Badge tone="neutral">{sourceModeLabels[followUp.source_mode]}</Badge>
                      <MathMarkdown muted>{followUp.tutor_answer}</MathMarkdown>
                      {followUp.visual_content ? <VisualRenderer visualContent={followUp.visual_content} /> : null}
                      <p className="text-xs font-medium text-primary">{followUp.next_action.replace("_", " ")}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {mcqs.length > 0 ? (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle>Quick check</CardTitle>
              <StudyToolsButton scope={`concept_${concept.concept_id}_quiz`} className="w-full sm:w-auto" />
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            {mcqs.map((question, questionIndex) => (
              <fieldset key={question.id} className="space-y-3 rounded-2xl border bg-background p-4">
                <legend className="px-1 text-sm font-semibold">
                  <span>{questionIndex + 1}. </span>
                  <MathMarkdown className="inline text-sm font-semibold" muted={false}>
                    {question.question_text}
                  </MathMarkdown>
                </legend>
                {question.question_type === "short_answer" ? (
                  <div className="space-y-2">
                    {question.evidence_guidance ? (
                      <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                        Use evidence: {question.evidence_guidance}
                      </p>
                    ) : null}
                    <textarea
                      className="min-h-32 w-full resize-y rounded-2xl border bg-background px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                      value={answers[String(question.id)] ?? ""}
                      onChange={(event) => setAnswer(question.id, event.target.value)}
                      placeholder="Write a short answer and support it with evidence from this section."
                      disabled={isBusy || Boolean(result)}
                    />
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {optionKeys.map((optionKey) => (
                      <label
                        key={optionKey}
                        className="flex min-h-14 cursor-pointer items-start gap-3 rounded-2xl border p-4 text-sm transition-colors hover:bg-muted"
                      >
                        <input
                          className="mt-1 h-4 w-4 shrink-0"
                          type="radio"
                          name={`question-${question.id}`}
                          value={optionKey}
                          checked={answers[String(question.id)] === optionKey}
                          onChange={() => setAnswer(question.id, optionKey)}
                          disabled={isBusy || Boolean(result)}
                        />
                        <div>
                          <span className="font-semibold">{optionKey}.</span>{" "}
                          <MathMarkdown className="inline" muted>
                            {question.options[optionKey] ?? ""}
                          </MathMarkdown>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </fieldset>
            ))}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground">
                Answered {answeredQuestionCount} of {mcqs.length}
              </p>
              <Button type="button" className="w-full sm:w-auto" onClick={handleSubmitAnswers} disabled={!canSubmit || Boolean(result)}>
                {loading === "submit" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
                Submit answers
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {result ? (
        <Card className={result.passed ? "border-emerald-300" : "border-rose-300"}>
          <CardHeader>
            <CardTitle>{result.passed ? "Ariel is ready to learn this!" : "Almost there"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              Score: {result.score}% ({result.correct_answers} of {result.total_questions} correct)
            </p>
            {result.passed ? null : (
              <FailedRemediationPanel
                message={result.remediation_message ?? "You did not pass this check yet. Choose how you want to continue."}
                remediation={result.remediation}
                isBusy={isBusy}
                onAskClarification={handleAskForClarification}
                onRestartConcept={handleRestartConcept}
                onRetryQuiz={handleRetryQuiz}
              />
            )}
            <p className="font-medium text-primary">
              {result.passed ? "Teach Ariel the concept in your own words, or keep your learning flow moving." : result.next_action}
            </p>
            {result.passed ? (
              <div className="grid gap-2 sm:flex sm:flex-wrap">
                <Button asChild variant="secondary" className="w-full sm:w-auto">
                  <Link href={subjectId ? `/subjects/${subjectId}#ariel` : "/subjects"}>
                    Teach Ariel now
                  </Link>
                </Button>
                <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={loadCurrentConcept} disabled={isBusy}>
                  Continue to next concept
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function FailedRemediationPanel({
  message,
  remediation,
  isBusy,
  onAskClarification,
  onRestartConcept,
  onRetryQuiz
}: {
  message: string;
  remediation: string;
  isBusy: boolean;
  onAskClarification: () => void;
  onRestartConcept: () => void;
  onRetryQuiz: () => void;
}) {
  return (
    <div className="space-y-4 rounded-3xl border border-rose-200 bg-rose-50/70 p-4 text-foreground">
      <div>
        <h3 className="text-base font-semibold">Almost there — let&apos;s strengthen this concept.</h3>
        <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      </div>
      {remediation ? (
        <div className="rounded-2xl bg-background/80 p-3">
          <MathMarkdown muted>{remediation}</MathMarkdown>
        </div>
      ) : null}
      <div className="grid gap-2 sm:grid-cols-3">
        <Button type="button" variant="secondary" className="w-full" onClick={onAskClarification} disabled={isBusy}>
          <MessageSquare className="h-4 w-4" aria-hidden="true" />
          Ask The Abbot for clarification
        </Button>
        <Button type="button" variant="outline" className="w-full" onClick={onRestartConcept} disabled={isBusy}>
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Restart concept
        </Button>
        <Button type="button" className="w-full" onClick={onRetryQuiz} disabled={isBusy}>
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Attempt quiz again
        </Button>
      </div>
    </div>
  );
}

function buildLiteratureCards(lesson: TutorLesson): LiteratureCard[] {
  const metadata = lesson.literary_metadata;
  if (!metadata) {
    return [];
  }

  return [
    {
      title: "What happened?",
      icon: BookOpen,
      content: compactText([metadata.summary, ...(metadata.key_events ?? [])])
    },
    {
      title: "Characters",
      icon: Users,
      content: compactText([...(metadata.characters_present ?? []), ...(metadata.character_development ?? [])])
    },
    {
      title: "Themes",
      icon: Sparkles,
      content: compactText([...(metadata.themes ?? []), ...(metadata.symbols ?? []).map((symbol) => `Symbol: ${symbol}`)])
    },
    {
      title: "Literary devices",
      icon: Feather,
      content: compactText(metadata.literary_devices ?? [])
    },
    {
      title: "Important quotes",
      icon: Quote,
      content: compactText(metadata.important_quotes ?? [])
    },
    {
      title: "Think about this",
      icon: Drama,
      content: compactText(metadata.interpretation_questions ?? [])
    }
  ].filter((card) => card.content.length > 0);
}

function compactText(values: Array<string | undefined>): string[] {
  return values
    .map((value) => value?.trim() ?? "")
    .filter(Boolean)
    .slice(0, 4);
}

function LiteratureLessonCards({ cards }: { cards: LiteratureCard[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <section key={card.title} className="rounded-lg border bg-muted/30 p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <h4 className="text-sm font-semibold">{card.title}</h4>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              {card.content.map((item, index) => (
                <MathMarkdown key={`${card.title}-${index}`} muted>
                  {item}
                </MathMarkdown>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
