"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bell,
  BookOpen,
  CalendarCheck,
  Flame,
  FolderOpen,
  Loader2,
  Plus,
  Sparkles,
  Upload
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getProgressDashboard, getSubjects } from "@/lib/api";
import type { DashboardDocument, DashboardResponse, ReinforcementRecommendation, Subject } from "@/lib/types";

export function DashboardClient() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const shouldWelcome = window.sessionStorage.getItem("signup_welcome") === "true";
    if (shouldWelcome) {
      window.sessionStorage.removeItem("signup_welcome");
      setShowWelcome(true);
    }

    async function loadDashboard() {
      try {
        const [dashboardResponse, subjectsResponse] = await Promise.all([
          getProgressDashboard(),
          getSubjects()
        ]);
        if (isMounted) {
          setDashboard(dashboardResponse);
          setSubjects(subjectsResponse);
        }
      } catch (caughtError) {
        if (isMounted) {
          setError(caughtError instanceof Error ? caughtError.message : "Unable to load dashboard.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      isMounted = false;
    };
  }, []);

  const activeDocument = useMemo(
    () => dashboard?.documents.find((document) => document.subject_id && document.current_recommended_next_action !== "document_complete") ?? null,
    [dashboard]
  );
  const activeSubject = activeDocument ? subjects.find((subject) => subject.id === activeDocument.subject_id) : null;
  const activeChapterTitle = activeDocument?.current_chapter_title ?? undefined;
  const activeConceptTitle = activeDocument?.current_concept_title ?? undefined;
  const reinforcementAlerts = dashboard?.student_ai_reinforcement?.recommendations ?? [];
  const memoryAlerts = dashboard?.teachback_memory_engine?.rusty_alerts ?? [];
  const recentDocuments = dashboard?.documents.slice(0, 3) ?? [];
  const streakCount = dashboard?.teachback_memory_engine?.reinforcement_streak.count ?? 0;

  if (isLoading) {
    return (
      <Card className="rounded-3xl">
        <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground sm:p-8">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Setting up your calm study space...
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
        <CardContent>
          <p className="text-sm text-muted-foreground">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!dashboard) {
    return null;
  }

  return (
    <div className="space-y-6">
      <WelcomeCard showWelcome={showWelcome} subjectCount={subjects.length} textbookCount={dashboard.documents.length} />

      <section className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <ContinueLearningCard
          activeDocument={activeDocument}
          activeSubject={activeSubject ?? null}
          activeChapterTitle={activeChapterTitle}
          activeConceptTitle={activeConceptTitle}
        />
        <DailyStreakCard streakCount={streakCount} />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <ShortcutCard
          icon={FolderOpen}
          title="Create subject"
          body="Start a focused space for one class, book, or exam."
          href="/subjects"
          action="New subject"
        />
        <ShortcutCard
          icon={Upload}
          title="Upload textbook"
          body="Choose a subject first, then add your PDF there."
          href={subjects[0] ? `/subjects/${subjects[0].id}#textbooks` : "/subjects"}
          action="Add PDF"
        />
        <OverviewCard subjects={subjects} documents={dashboard.documents} />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <SubjectsOverview subjects={subjects} documents={dashboard.documents} />
        <AlertsPanel reinforcementAlerts={reinforcementAlerts} memoryAlerts={memoryAlerts} />
      </section>

      <RecentActivity documents={recentDocuments} />
    </div>
  );
}

function WelcomeCard({
  showWelcome,
  subjectCount,
  textbookCount
}: {
  showWelcome: boolean;
  subjectCount: number;
  textbookCount: number;
}) {
  const headline = showWelcome ? "Welcome in. Your study space is ready." : "Welcome back.";
  const body = subjectCount === 0
    ? "Create a subject, add a textbook, and The Abbot will prepare a clean learning path."
    : textbookCount === 0
      ? "Your subjects are ready. Add a textbook when you want The Abbot to build lessons."
      : "Pick one small study round, keep Ariel warm, and let the rest wait its turn.";

  return (
    <Card className="overflow-hidden rounded-3xl border-primary/10 bg-card/95 shadow-sm">
      <CardContent className="p-6 sm:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-semibold tracking-normal">{headline}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
          </div>
          <Button asChild className="w-full sm:w-auto">
            <Link href="/subjects">
              Open subjects
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ContinueLearningCard({
  activeDocument,
  activeSubject,
  activeChapterTitle,
  activeConceptTitle
}: {
  activeDocument: DashboardDocument | null;
  activeSubject: Subject | null;
  activeChapterTitle?: string;
  activeConceptTitle?: string;
}) {
  if (!activeDocument || !activeSubject) {
    return (
      <Card className="rounded-3xl">
        <CardContent className="p-6">
          <p className="text-sm font-medium text-primary">Continue learning</p>
          <h2 className="mt-2 text-xl font-semibold">Nothing urgent today</h2>
          <p className="mt-2 text-sm text-muted-foreground">Create a subject or open one to upload a textbook.</p>
          <Button asChild className="mt-5 w-full sm:w-auto">
            <Link href="/subjects">Choose a subject</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-3xl border-primary/20 shadow-sm">
      <CardContent className="p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">Continue learning</p>
            <h2 className="mt-2 text-2xl font-semibold">{activeConceptTitle ?? activeDocument.title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {activeSubject.name}{activeChapterTitle ? ` - ${activeChapterTitle}` : ""}
            </p>
          </div>
          <Button asChild className="w-full sm:w-auto">
            <Link href={`/subjects/${activeSubject.id}`}>
              Continue
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function DailyStreakCard({ streakCount }: { streakCount: number }) {
  return (
    <Card className="rounded-3xl">
      <CardContent className="p-6">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
            <Flame className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Daily streak</p>
            <p className="mt-1 text-3xl font-semibold">{streakCount}</p>
            <p className="mt-1 text-sm text-muted-foreground">Ariel rescue rhythm</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ShortcutCard({
  icon: Icon,
  title,
  body,
  href,
  action
}: {
  icon: typeof FolderOpen;
  title: string;
  body: string;
  href: string;
  action: string;
}) {
  return (
    <Card className="rounded-3xl">
      <CardContent className="flex h-full flex-col p-5">
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <h3 className="font-semibold">{title}</h3>
        <p className="mt-2 flex-1 text-sm leading-6 text-muted-foreground">{body}</p>
        <Button asChild variant="outline" className="mt-4 w-full">
          <Link href={href}>
            {action}
            <Plus className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function OverviewCard({ subjects, documents }: { subjects: Subject[]; documents: DashboardDocument[] }) {
  const progress = overallProgress(documents);
  return (
    <Card className="rounded-3xl">
      <CardContent className="p-5">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
            <CalendarCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="font-semibold">Learning journey</h3>
            <p className="text-sm text-muted-foreground">{subjects.length} subjects, {documents.length} textbooks</p>
          </div>
        </div>
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Overall progress</span>
          <span className="font-semibold">{progress}%</span>
        </div>
        <Progress value={Number(progress)} />
      </CardContent>
    </Card>
  );
}

function SubjectsOverview({ subjects, documents }: { subjects: Subject[]; documents: DashboardDocument[] }) {
  return (
    <Card className="rounded-3xl">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <div>
          <CardTitle>Subjects overview</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Open one workspace at a time.</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/subjects">View all</Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {subjects.length > 0 ? subjects.slice(0, 4).map((subject) => {
          const subjectDocuments = documents.filter((document) => document.subject_id === subject.id);
          return (
            <Link key={subject.id} className="flex items-center justify-between gap-3 rounded-2xl border bg-background p-3 transition hover:bg-muted" href={`/subjects/${subject.id}`}>
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <FolderOpen className="h-4 w-4" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{subject.name}</p>
                  <p className="text-xs text-muted-foreground">{subjectDocuments.length} textbook{subjectDocuments.length === 1 ? "" : "s"}</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            </Link>
          );
        }) : (
          <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">No subjects yet. Start with one simple study space.</p>
        )}
      </CardContent>
    </Card>
  );
}

function AlertsPanel({
  reinforcementAlerts,
  memoryAlerts
}: {
  reinforcementAlerts: ReinforcementRecommendation[];
  memoryAlerts: ReinforcementRecommendation[];
}) {
  const alerts = [...reinforcementAlerts, ...memoryAlerts].slice(0, 3);
  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
          <CardTitle>Gentle alerts</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.length > 0 ? alerts.map((alert) => (
          <div key={`${alert.id}-${alert.concept_id}`} className="rounded-2xl border bg-background p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="truncate text-sm font-semibold">{alert.concept_title}</p>
              <Badge tone="in_progress">{alert.priority}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">{alert.friendly_message ?? alert.reason}</p>
          </div>
        )) : (
          <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">No rescue missions right now. Ariel is cruising.</p>
        )}
      </CardContent>
    </Card>
  );
}

function RecentActivity({ documents }: { documents: DashboardDocument[] }) {
  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <CardTitle>Recent activity</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {documents.length > 0 ? documents.map((document) => (
          <div key={document.document_id} className="flex flex-col gap-2 rounded-2xl border bg-background p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{document.title}</p>
              <p className="text-xs text-muted-foreground">{document.subject_name ?? "No subject"} - {friendlyStatus(document.status)}</p>
            </div>
            <Badge tone={document.current_recommended_next_action === "document_complete" ? "passed" : "available"}>
              {document.completion_percentage}%
            </Badge>
          </div>
        )) : (
          <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">Your recent study moments will appear here.</p>
        )}
      </CardContent>
    </Card>
  );
}

function overallProgress(documents: DashboardDocument[]): string {
  if (documents.length === 0) {
    return "0.00";
  }
  const total = documents.reduce((sum, document) => sum + Number(document.completion_percentage), 0);
  return (total / documents.length).toFixed(2);
}

function friendlyStatus(status: string): string {
  const labels: Record<string, string> = {
    uploaded: "Preparing your textbook",
    extracting_text: "Reading your PDF",
    chapters_detected: "Chapters found",
    processing_concepts: "Finding what you need to learn",
    ready: "Ready to study",
    failed: "Needs a retry"
  };
  return labels[status] ?? status.replaceAll("_", " ");
}
