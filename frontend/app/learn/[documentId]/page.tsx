import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { ProtectedPage } from "@/components/auth/protected-page";
import { StudySessionClient } from "@/components/learning/study-session-client";
import { Button } from "@/components/ui/button";

export default async function LearnPage({
  params,
  searchParams
}: {
  params: Promise<{ documentId: string }>;
  searchParams: Promise<{ subject?: string }>;
}) {
  const { documentId } = await params;
  const { subject } = await searchParams;
  const backHref = subject ? `/subjects/${subject}` : "/subjects";
  const subjectId = subject ? Number(subject) : undefined;

  return (
    <main className="mx-auto min-h-screen w-full max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
      <ProtectedPage>
        <>
          <Button asChild variant="outline" size="sm">
            <Link href={backHref}>
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to subject
            </Link>
          </Button>
          <section className="mt-6 space-y-2">
            <p className="text-sm font-medium text-primary">Study round</p>
            <h1 className="text-3xl font-semibold tracking-normal">Learn with The Abbot</h1>
          </section>
          <section className="mt-5">
            <StudySessionClient documentId={documentId} subjectId={Number.isFinite(subjectId) ? subjectId : undefined} />
          </section>
        </>
      </ProtectedPage>
    </main>
  );
}
