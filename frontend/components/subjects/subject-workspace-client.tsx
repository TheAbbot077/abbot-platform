"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  FolderOpen,
  GraduationCap,
  Layers3,
  Loader2,
  RotateCcw,
  Settings,
  Sparkles,
  Upload
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ChapterSection } from "@/components/dashboard/chapter-section";
import { DocumentCard } from "@/components/dashboard/document-card";
import { MemoryEnginePanel, type ArielLearningConcept } from "@/components/dashboard/memory-engine-panel";
import { SubjectUploadPanel } from "@/components/dashboard/subject-upload-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getProgressDashboard, getSubjects } from "@/lib/api";
import type { DashboardDocument, DashboardResponse, ReinforcementRecommendation, Subject, TeachBackMemoryEngine } from "@/lib/types";

type WorkspaceTab = "overview" | "textbooks" | "concepts" | "abbot" | "ariel" | "progress" | "reinforcement" | "settings";

const tabs: Array<{ id: WorkspaceTab; label: string; icon: LucideIcon }> = [
  { id: "overview", label: "Overview", icon: Sparkles },
  { id: "textbooks", label: "Textbooks", icon: BookOpen },
  { id: "concepts", label: "Concepts", icon: Layers3 },
  { id: "abbot", label: "The Abbot", icon: GraduationCap },
  { id: "ariel", label: "Ariel", icon: BrainCircuit },
  { id: "progress", label: "Progress", icon: CheckCircle2 },
  { id: "reinforcement", label: "Reinforcement", icon: RotateCcw },
  { id: "settings", label: "Settings", icon: Settings }
];

function isWorkspaceTab(value: string): value is WorkspaceTab {
  return tabs.some((tab) => tab.id === value);
}

export function SubjectWorkspaceClient({ subjectId }: { subjectId: number }) {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadWorkspace() {
    setError(null);
    const [dashboardResponse, subjectsResponse] = await Promise.all([
      getProgressDashboard(subjectId),
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
          getProgressDashboard(subjectId),
          getSubjects()
        ]);
        if (isMounted) {
          setDashboard(dashboardResponse);
          setSubjects(subjectsResponse);
        }
      } catch (caught) {
        if (isMounted) {
          setError(caught instanceof Error ? caught.message : "Unable to load this subject.");
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
  }, [subjectId]);

  useEffect(() => {
    function syncHashTab() {
      const hashTab = window.location.hash.replace("#", "");
      if (isWorkspaceTab(hashTab)) {
        setActiveTab(hashTab);
      } else {
        setActiveTab("overview");
      }
    }

    syncHashTab();
    window.addEventListener("hashchange", syncHashTab);
    return () => window.removeEventListener("hashchange", syncHashTab);
  }, [subjectId]);

  const subject = subjects.find((item) => item.id === subjectId) ?? null;
  const documents = useMemo(
    () => dashboard?.documents.filter((document) => document.subject_id === subjectId) ?? [],
    [dashboard, subjectId]
  );
  const activeDocument = documents.find(canStudyDocument) ?? documents[0];
  const activeChapter = activeDocument?.chapters.find((chapter) => Number(chapter.completion_percentage) < 100);
  const activeConcept = activeChapter?.concepts.find((concept) => ["available", "in_progress", "failed"].includes(concept.status));
  const completion = subjectCompletion(documents);
  const subjectMemoryEngine = filterMemoryEngine(dashboard?.teachback_memory_engine, documents);
  const reinforcementAlerts = filterRecommendations(dashboard?.student_ai_reinforcement?.recommendations ?? [], documents);

  async function refreshWorkspace() {
    setIsLoading(true);
    try {
      await loadWorkspace();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to refresh this subject.");
    } finally {
      setIsLoading(false);
    }
  }

  function selectTab(tab: WorkspaceTab) {
    setActiveTab(tab);
    const nextUrl = new URL(window.location.href);
    nextUrl.hash = tab;
    window.history.replaceState(null, "", nextUrl);
  }

  if (isLoading && !dashboard) {
    return (
      <Card className="rounded-3xl">
        <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Opening your subject workspace...
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
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button asChild variant="outline">
            <Link href="/subjects">Back to subjects</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!subject) {
    return (
      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Subject not found</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">This subject may have been deleted, or it belongs to another account.</p>
          <Button asChild variant="outline">
            <Link href="/subjects">Back to subjects</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <WorkspaceHero
        subject={subject}
        documents={documents}
        activeDocument={activeDocument}
        activeChapterTitle={activeChapter?.title}
        activeConceptTitle={activeConcept?.title}
        completion={completion}
      />

      <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
        <SubjectNavigation subjectName={subject.name} activeTab={activeTab} onSelect={selectTab} />
        <div className="min-w-0 space-y-5">
          <MobileSubjectNavigation subjectName={subject.name} activeTab={activeTab} onSelect={selectTab} />

          {activeTab === "overview" ? (
            <ContinueSection subject={subject} activeDocument={activeDocument} activeChapterTitle={activeChapter?.title} activeConceptTitle={activeConcept?.title} />
          ) : null}

          {activeTab === "textbooks" ? (
            <TextbooksSection subject={subject} subjects={subjects} documents={documents} onChanged={refreshWorkspace} />
          ) : null}

          {activeTab === "concepts" ? (
            <ConceptsSection documents={documents} onChanged={refreshWorkspace} />
          ) : null}

          {activeTab === "abbot" ? (
            <AbbotSection subject={subject} activeDocument={activeDocument} activeChapterTitle={activeChapter?.title} activeConceptTitle={activeConcept?.title} />
          ) : null}

          {activeTab === "ariel" ? (
            <ArielSection subjectId={subject.id} documents={documents} engine={subjectMemoryEngine} onChanged={refreshWorkspace} />
          ) : null}

          {activeTab === "progress" ? (
            <ProgressSection documents={documents} completion={completion} />
          ) : null}

          {activeTab === "reinforcement" ? (
            <ReinforcementSection alerts={reinforcementAlerts} />
          ) : null}

          {activeTab === "settings" ? (
            <SubjectSettingsSection subject={subject} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SubjectNavigation({
  subjectName,
  activeTab,
  onSelect
}: {
  subjectName: string;
  activeTab: WorkspaceTab;
  onSelect: (tab: WorkspaceTab) => void;
}) {
  return (
    <aside className="hidden lg:block">
      <div className="sticky top-5 rounded-3xl border bg-card p-3 shadow-sm">
        <div className="px-3 py-2">
          <p className="text-xs font-medium uppercase text-muted-foreground">Current subject</p>
          <h2 className="mt-1 truncate text-lg font-semibold">{subjectName}</h2>
        </div>
        <nav className="mt-2 space-y-1" aria-label={`${subjectName} navigation`}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={`flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left text-sm font-medium transition ${isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
                onClick={() => onSelect(tab.id)}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="truncate">{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}

function MobileSubjectNavigation({
  subjectName,
  activeTab,
  onSelect
}: {
  subjectName: string;
  activeTab: WorkspaceTab;
  onSelect: (tab: WorkspaceTab) => void;
}) {
  return (
    <div className="sticky top-3 z-10 rounded-3xl border bg-card/95 p-3 shadow-sm backdrop-blur lg:hidden">
      <label className="text-xs font-medium uppercase text-muted-foreground" htmlFor="subject-workspace-nav">
        {subjectName}
      </label>
      <select
        id="subject-workspace-nav"
        className="mt-2 min-h-11 w-full rounded-2xl border bg-background px-3 text-sm font-medium"
        value={activeTab}
        onChange={(event) => onSelect(event.target.value as WorkspaceTab)}
      >
        {tabs.map((tab) => (
          <option key={tab.id} value={tab.id}>
            {tab.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function WorkspaceHero({
  subject,
  documents,
  activeDocument,
  activeChapterTitle,
  activeConceptTitle,
  completion
}: {
  subject: Subject;
  documents: DashboardDocument[];
  activeDocument?: DashboardDocument;
  activeChapterTitle?: string;
  activeConceptTitle?: string;
  completion: string;
}) {
  return (
    <div className="rounded-3xl border bg-card p-5 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Button asChild variant="outline" size="sm" className="w-full sm:w-auto">
            <Link href="/subjects">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Subjects
            </Link>
          </Button>
          <p className="mt-5 text-sm font-medium text-primary">Subject Workspace</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">{subject.name}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Everything here is scoped to this subject: textbooks, concepts, The Abbot, Ariel, progress, and reinforcement.
          </p>
        </div>
        {activeDocument && canStudyDocument(activeDocument) ? (
          <Button asChild className="w-full lg:w-auto">
            <Link href={`/learn/${activeDocument.document_id}?subject=${subject.id}`}>
              Continue with The Abbot
              <Sparkles className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        ) : null}
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <WorkspaceStat icon={BookOpen} label="Textbooks" value={String(documents.length)} />
        <WorkspaceStat icon={Layers3} label="Concepts" value={String(conceptCount(documents))} />
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-semibold">{completion}%</span>
            </div>
            <Progress value={Number(completion)} />
            <p className="mt-2 truncate text-xs text-muted-foreground">{activeConceptTitle ?? activeChapterTitle ?? "Ready when you are."}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ContinueSection({
  subject,
  activeDocument,
  activeChapterTitle,
  activeConceptTitle
}: {
  subject: Subject;
  activeDocument?: DashboardDocument;
  activeChapterTitle?: string;
  activeConceptTitle?: string;
}) {
  return (
    <Card className="rounded-3xl border-primary/20">
      <CardHeader>
        <CardTitle>Continue Learning</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        {activeDocument && canStudyDocument(activeDocument) ? (
          <>
            <div className="space-y-1">
              <p className="text-lg font-semibold">{activeConceptTitle ?? activeDocument.title}</p>
              <p className="text-sm text-muted-foreground">
                {activeChapterTitle ? `${activeDocument.title} - ${activeChapterTitle}` : activeDocument.title}
              </p>
            </div>
            <Button asChild className="w-full md:w-auto">
              <Link href={`/learn/${activeDocument.document_id}?subject=${subject.id}`}>Start study round</Link>
            </Button>
          </>
        ) : activeDocument?.current_recommended_next_action === "wait_for_concepts" ? (
          <div>
            <p className="font-semibold">The Abbot is preparing lessons</p>
            <p className="mt-1 text-sm text-muted-foreground">Your chapters are being organized into teachable concepts. Check back in a moment.</p>
          </div>
        ) : activeDocument?.current_recommended_next_action === "concepts_missing" ? (
          <div>
            <p className="font-semibold">Lessons need a quick retry</p>
            <p className="mt-1 text-sm text-muted-foreground">This textbook has chapters but no concepts yet. Re-run concept extraction or reprocess the textbook.</p>
          </div>
        ) : (
          <div>
            <p className="font-semibold">No textbook yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Add a PDF in the Textbooks tab to begin.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TextbooksSection({
  subject,
  subjects,
  documents,
  onChanged
}: {
  subject: Subject;
  subjects: Subject[];
  documents: DashboardDocument[];
  onChanged: () => void;
}) {
  return (
    <section className="space-y-4">
      <SubjectUploadPanel subjects={subjects} fixedSubjectId={subject.id} onChanged={onChanged} />
      {documents.length > 0 ? (
        documents.map((document) => <DocumentCard key={document.document_id} document={document} onChanged={onChanged} />)
      ) : (
        <EmptyWorkspaceCard icon={Upload} title="No textbooks here yet" body="Upload a PDF to start building this subject's ordered learning path." />
      )}
    </section>
  );
}

function AbbotSection({
  subject,
  activeDocument,
  activeChapterTitle,
  activeConceptTitle
}: {
  subject: Subject;
  activeDocument?: DashboardDocument;
  activeChapterTitle?: string;
  activeConceptTitle?: string;
}) {
  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <CardTitle>The Abbot</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">The Abbot teaches only the currently unlocked concept in this subject's selected textbook.</p>
        {activeDocument && canStudyDocument(activeDocument) ? (
          <div className="rounded-2xl border bg-background p-4">
            <p className="text-sm font-semibold">{activeConceptTitle ?? activeDocument.title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{activeChapterTitle ?? "All chapters complete"}</p>
            <Button asChild className="mt-4 w-full sm:w-auto">
              <Link href={`/learn/${activeDocument.document_id}?subject=${subject.id}`}>Learn with The Abbot</Link>
            </Button>
          </div>
        ) : activeDocument?.current_recommended_next_action === "wait_for_concepts" ? (
          <EmptyWorkspaceCard icon={GraduationCap} title="The Abbot is preparing lessons" body="Your textbook is uploaded. The Abbot is still finding what you need to learn." />
        ) : activeDocument?.current_recommended_next_action === "concepts_missing" ? (
          <EmptyWorkspaceCard icon={GraduationCap} title="Lessons need a quick retry" body="This textbook has chapters but no concepts yet. Re-run missing concept extraction or reprocess the textbook." />
        ) : (
          <EmptyWorkspaceCard icon={GraduationCap} title="The Abbot is waiting" body="Upload a textbook first, then The Abbot will guide the next concept." />
        )}
      </CardContent>
    </Card>
  );
}

function ArielSection({
  subjectId,
  documents,
  engine,
  onChanged
}: {
  subjectId: number;
  documents: DashboardDocument[];
  engine?: TeachBackMemoryEngine;
  onChanged: () => void;
}) {
  const learningConcepts = buildArielLearningConcepts(documents);
  const teachableConcepts = learningConcepts.filter((concept) => concept.learning_state !== "locked");
  const chapterExamReady = learningConcepts.some((concept) => concept.examiner_unlocked);

  if (teachableConcepts.length === 0 && (!engine || engine.daily_rescue_missions.length === 0)) {
    return (
      <EmptyWorkspaceCard
        icon={BrainCircuit}
        title="Pass your first concept to start teaching Ariel."
        body="Once you pass a concept, Ariel can learn your explanation. Future and locked concepts stay off-limits."
      />
    );
  }

  return (
    <section className="space-y-4">
      <Card className="rounded-3xl">
        <CardContent className="p-5">
          <p className="text-sm font-semibold text-primary">
            {chapterExamReady ? "Ariel is ready for the chapter exam." : "Ariel is ready to learn what you've mastered."}
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            {chapterExamReady
              ? "You completed a chapter, so examiner checks are now available for taught concepts in that chapter."
              : "Teach Ariel any concept you've already passed. Finish this chapter to submit Ariel to the examiner."}
          </p>
        </CardContent>
      </Card>
      <MemoryEnginePanel engine={engine} subjectId={subjectId} learningConcepts={learningConcepts} onChanged={onChanged} />
    </section>
  );
}

function ConceptsSection({ documents, onChanged }: { documents: DashboardDocument[]; onChanged: () => void }) {
  return (
    <section className="space-y-4">
      {documents.length > 0 ? documents.map((document) => (
        <Card key={document.document_id} className="rounded-3xl">
          <CardHeader>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>{document.title}</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">Chapters and concepts stay in original sequence order.</p>
              </div>
              <Badge tone={document.current_recommended_next_action === "document_complete" ? "passed" : "available"}>{document.completion_percentage}%</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {document.chapters.map((chapter) => (
              <ChapterSection key={chapter.chapter_id} chapter={chapter} onChanged={onChanged} />
            ))}
          </CardContent>
        </Card>
      )) : (
        <EmptyWorkspaceCard icon={Layers3} title="No concepts yet" body="Concepts appear here after a textbook is processed." />
      )}
    </section>
  );
}

function ProgressSection({ documents, completion }: { documents: DashboardDocument[]; completion: string }) {
  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <CardTitle>Progress</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Subject completion</span>
            <span className="font-semibold">{completion}%</span>
          </div>
          <Progress value={Number(completion)} />
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <WorkspaceStat icon={BookOpen} label="Textbooks" value={String(documents.length)} />
          <WorkspaceStat icon={Layers3} label="Concepts" value={String(conceptCount(documents))} />
          <WorkspaceStat icon={CheckCircle2} label="Passed" value={String(passedConceptCount(documents))} />
        </div>
      </CardContent>
    </Card>
  );
}

function ReinforcementSection({ alerts }: { alerts: ReinforcementRecommendation[] }) {
  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <CardTitle>Reinforcement</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.length > 0 ? alerts.map((alert) => (
          <div key={`${alert.id}-${alert.concept_id}`} className="rounded-2xl border bg-background p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="font-semibold">{alert.mission_title ?? `Review ${alert.concept_title}`}</p>
                <p className="mt-1 text-sm text-muted-foreground">{alert.friendly_message ?? alert.reason}</p>
              </div>
              <Badge tone="in_progress">{alert.priority}</Badge>
            </div>
          </div>
        )) : (
          <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">No reinforcement alerts for this subject right now.</p>
        )}
      </CardContent>
    </Card>
  );
}

function SubjectSettingsSection({ subject }: { subject: Subject }) {
  return (
    <Card className="rounded-3xl">
      <CardHeader>
        <CardTitle>Subject Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>Subject name: <span className="font-medium text-foreground">{subject.name}</span></p>
        <p>Delete subjects from the main Subjects page. Textbooks must be removed first so progress is not deleted accidentally.</p>
        <Button asChild variant="outline" className="w-full sm:w-auto">
          <Link href="/subjects">Manage subjects</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function WorkspaceStat({ icon: Icon, label, value }: { icon: typeof BookOpen; label: string; value: string }) {
  return (
    <Card className="rounded-2xl">
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-xl font-semibold">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyWorkspaceCard({ icon: Icon, title, body }: { icon: typeof Upload; title: string; body: string }) {
  return (
    <Card className="rounded-3xl">
      <CardContent className="p-5 text-center sm:p-8">
        <Icon className="mx-auto mb-3 h-8 w-8 text-primary" aria-hidden="true" />
        <h3 className="font-semibold">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{body}</p>
      </CardContent>
    </Card>
  );
}

function conceptCount(documents: DashboardDocument[]): number {
  return documents.reduce(
    (total, document) => total + document.chapters.reduce((chapterTotal, chapter) => chapterTotal + chapter.concepts.length, 0),
    0
  );
}

function passedConceptCount(documents: DashboardDocument[]): number {
  return documents.reduce(
    (total, document) => total + document.chapters.reduce(
      (chapterTotal, chapter) => chapterTotal + chapter.concepts.filter((concept) => concept.status === "passed").length,
      0
    ),
    0
  );
}

function canStudyDocument(document: DashboardDocument): boolean {
  return ["start_current_concept", "continue_current_concept"].includes(document.current_recommended_next_action);
}

function subjectCompletion(documents: DashboardDocument[]): string {
  if (documents.length === 0) {
    return "0.00";
  }
  const total = documents.reduce((sum, document) => sum + Number(document.completion_percentage), 0);
  return (total / documents.length).toFixed(2);
}

function filterMemoryEngine(engine: TeachBackMemoryEngine | undefined, documents: DashboardDocument[]): TeachBackMemoryEngine | undefined {
  if (!engine) {
    return undefined;
  }
  const documentIds = new Set(documents.map((document) => document.document_id));
  const daily_rescue_missions = engine.daily_rescue_missions.filter((mission) => documentIds.has(mission.document_id));
  const rusty_alerts = engine.rusty_alerts.filter((mission) => documentIds.has(mission.document_id));
  return {
    ...engine,
    daily_rescue_missions,
    rusty_alerts
  };
}

function filterRecommendations(recommendations: ReinforcementRecommendation[], documents: DashboardDocument[]): ReinforcementRecommendation[] {
  const documentIds = new Set(documents.map((document) => document.document_id));
  return recommendations.filter((recommendation) => documentIds.has(recommendation.document_id));
}

function buildArielLearningConcepts(documents: DashboardDocument[]): ArielLearningConcept[] {
  return documents.flatMap((document) =>
    document.chapters.flatMap((chapter) =>
      chapter.concepts
        .map((concept) => ({
          concept_id: concept.concept_id,
          concept_title: concept.title,
          chapter_id: chapter.chapter_id,
          chapter_title: chapter.title,
          document_title: document.title,
          ariel_taught: Boolean(concept.ariel_taught),
          examiner_unlocked: Boolean(chapter.ariel_examiner_unlocked),
          learning_state: concept.status !== "passed" || concept.ariel_teachable === false
            ? "locked"
            : concept.ariel_taught
              ? "taught"
              : "ready",
        }))
    )
  );
}
