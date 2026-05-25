"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bell,
  BookOpen,
  FolderOpen,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2
} from "lucide-react";

import { SubjectUploadPanel } from "@/components/dashboard/subject-upload-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { deleteSubject, getProgressDashboard, getSubjects } from "@/lib/api";
import type { DashboardDocument, DashboardResponse, ReinforcementRecommendation, Subject } from "@/lib/types";

type SubjectCardData = {
  subject: Subject;
  documents: DashboardDocument[];
  progress: string;
  activeChapterTitle: string;
  activeConceptTitle: string;
  alerts: ReinforcementRecommendation[];
};

export function SubjectsClient() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "needs_attention" | "empty">("all");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingSubjectId, setDeletingSubjectId] = useState<number | null>(null);

  async function loadSubjects() {
    const [dashboardResponse, subjectsResponse] = await Promise.all([
      getProgressDashboard(),
      getSubjects()
    ]);
    setDashboard(dashboardResponse);
    setSubjects(subjectsResponse);
  }

  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        const [dashboardResponse, subjectsResponse] = await Promise.all([
          getProgressDashboard(),
          getSubjects()
        ]);
        if (isMounted) {
          setDashboard(dashboardResponse);
          setSubjects(subjectsResponse);
        }
      } catch (caught) {
        if (isMounted) {
          setError(caught instanceof Error ? caught.message : "Unable to load subjects.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      isMounted = false;
    };
  }, []);

  const subjectCards = useMemo(
    () => buildSubjectCards(subjects, dashboard),
    [subjects, dashboard]
  );
  const filteredCards = useMemo(
    () => filterSubjectCards(subjectCards, query, statusFilter),
    [subjectCards, query, statusFilter]
  );

  async function refresh() {
    setIsLoading(true);
    try {
      await loadSubjects();
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to refresh subjects.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteSubject(card: SubjectCardData) {
    const subject = card.subject;
    const confirmed = window.confirm(
      card.documents.length > 0
        ? `Delete subject "${subject.name}"? Delete or move its textbooks first.`
        : `Delete subject "${subject.name}"? This cannot be undone.`
    );
    if (!confirmed) {
      return;
    }

    setDeletingSubjectId(subject.id);
    setMessage(null);
    try {
      await deleteSubject(subject.id);
      setMessage(`"${subject.name}" was deleted.`);
      await loadSubjects();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not delete this subject.");
    } finally {
      setDeletingSubjectId(null);
    }
  }

  if (isLoading && !dashboard) {
    return (
      <Card className="rounded-3xl">
        <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading your subjects...
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>The Abbot needs a moment</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">{error}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <SubjectUploadPanel subjects={subjects} onChanged={refresh} />

      <section className="rounded-3xl border bg-card p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Your subjects</h2>
            <p className="mt-1 text-sm text-muted-foreground">Search, scan, and open one focused workspace.</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="relative w-full sm:w-auto">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <input
                className="min-h-11 w-full rounded-full border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring sm:w-64"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search subjects"
              />
            </label>
            <select
              className="min-h-11 w-full rounded-full border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring sm:w-auto"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}
            >
              <option value="all">All subjects</option>
              <option value="active">Active</option>
              <option value="needs_attention">Needs a boost</option>
              <option value="empty">No textbooks yet</option>
            </select>
          </div>
        </div>
        {message ? <p className="mt-3 rounded-2xl bg-muted px-4 py-3 text-sm text-muted-foreground">{message}</p> : null}
      </section>

      {filteredCards.length > 0 ? (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredCards.map((card, index) => (
            <SubjectCard
              key={card.subject.id}
              card={card}
              accentClass={accentClasses[index % accentClasses.length]}
              isDeleting={deletingSubjectId === card.subject.id}
              onDelete={() => handleDeleteSubject(card)}
            />
          ))}
        </section>
      ) : subjects.length > 0 ? (
        <Card className="rounded-3xl">
          <CardContent className="p-5 text-center sm:p-8">
            <Search className="mx-auto mb-3 h-8 w-8 text-primary" aria-hidden="true" />
            <h2 className="text-xl font-semibold">No matching subjects</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">Try a different search or filter.</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-3xl">
          <CardContent className="p-5 text-center sm:p-8">
            <Plus className="mx-auto mb-3 h-8 w-8 text-primary" aria-hidden="true" />
            <h2 className="text-xl font-semibold">Create your first subject</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              Subjects keep your textbooks, concepts, The Abbot sessions, and Ariel practice nicely focused.
            </p>
          </CardContent>
        </Card>
      )}

      {dashboard?.documents.some((document) => document.subject_id === null) ? (
        <Card className="rounded-3xl border-secondary/50">
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <BookOpen className="mt-1 h-5 w-5 text-primary" aria-hidden="true" />
              <div>
                <p className="font-semibold">Some textbooks are not in a subject yet</p>
                <p className="text-sm text-muted-foreground">Upload future textbooks from inside a subject workspace for the cleanest flow.</p>
              </div>
            </div>
            <Sparkles className="hidden h-5 w-5 text-primary sm:block" aria-hidden="true" />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function SubjectCard({
  card,
  accentClass,
  isDeleting,
  onDelete
}: {
  card: SubjectCardData;
  accentClass: string;
  isDeleting: boolean;
  onDelete: () => void;
}) {
  const hasAlerts = card.alerts.length > 0;
  return (
    <Card className="overflow-hidden rounded-3xl shadow-sm">
      <div className={`h-2 ${accentClass}`} />
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
              <FolderOpen className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <CardTitle className="truncate text-lg">{card.subject.name}</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {card.documents.length} textbook{card.documents.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>
          {hasAlerts ? <Badge tone="in_progress">Boost</Badge> : <Badge tone="neutral">Calm</Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Subject progress</span>
            <span className="font-semibold">{card.progress}%</span>
          </div>
          <Progress value={Number(card.progress)} />
        </div>

        <div className="rounded-2xl bg-muted/60 p-4">
          <p className="text-xs font-medium text-muted-foreground">Current focus</p>
          <p className="mt-1 truncate text-sm font-semibold">{card.activeConceptTitle}</p>
          <p className="mt-1 truncate text-xs text-muted-foreground">{card.activeChapterTitle}</p>
        </div>

        {hasAlerts ? (
          <div className="rounded-2xl border bg-background p-3">
            <div className="mb-1 flex items-center gap-2">
              <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
              <p className="text-sm font-semibold">Reinforcement ready</p>
            </div>
            <p className="line-clamp-2 text-sm text-muted-foreground">
              {card.alerts[0].friendly_message ?? card.alerts[0].reason}
            </p>
          </div>
        ) : null}

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button asChild className="flex-1">
            <Link href={`/subjects/${card.subject.id}`}>
              Open workspace
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
          <Button type="button" variant="outline" className="flex-1" onClick={onDelete} disabled={isDeleting}>
            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

const accentClasses = [
  "bg-primary",
  "bg-secondary",
  "bg-emerald-400",
  "bg-sky-400",
  "bg-rose-400"
];

function buildSubjectCards(subjects: Subject[], dashboard: DashboardResponse | null): SubjectCardData[] {
  const documents = dashboard?.documents ?? [];
  const alerts = [
    ...(dashboard?.student_ai_reinforcement?.recommendations ?? []),
    ...(dashboard?.teachback_memory_engine?.rusty_alerts ?? [])
  ];

  return subjects.map((subject) => {
    const subjectDocuments = documents.filter((document) => document.subject_id === subject.id);
    const activeDocument = subjectDocuments.find((document) => document.current_recommended_next_action !== "document_complete") ?? subjectDocuments[0];
    const documentIds = new Set(subjectDocuments.map((document) => document.document_id));

    return {
      subject,
      documents: subjectDocuments,
      progress: subjectProgress(subjectDocuments),
      activeChapterTitle: activeDocument?.current_chapter_title ?? (activeDocument ? "All chapters complete" : "Add a textbook to begin"),
      activeConceptTitle: activeDocument?.current_concept_title ?? activeDocument?.title ?? "No active concept yet",
      alerts: alerts.filter((alert) => documentIds.has(alert.document_id))
    };
  });
}

function filterSubjectCards(cards: SubjectCardData[], query: string, statusFilter: "all" | "active" | "needs_attention" | "empty") {
  const normalizedQuery = query.trim().toLowerCase();
  return cards.filter((card) => {
    const matchesQuery = !normalizedQuery || card.subject.name.toLowerCase().includes(normalizedQuery);
    const matchesStatus =
      statusFilter === "all"
      || (statusFilter === "active" && card.documents.length > 0 && Number(card.progress) < 100)
      || (statusFilter === "needs_attention" && card.alerts.length > 0)
      || (statusFilter === "empty" && card.documents.length === 0);
    return matchesQuery && matchesStatus;
  });
}

function subjectProgress(documents: DashboardDocument[]): string {
  if (documents.length === 0) {
    return "0.00";
  }
  const total = documents.reduce((sum, document) => sum + Number(document.completion_percentage), 0);
  return (total / documents.length).toFixed(2);
}
