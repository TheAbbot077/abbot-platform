import { ProtectedPage } from "@/components/auth/protected-page";
import { SubjectWorkspaceClient } from "@/components/subjects/subject-workspace-client";

export default async function SubjectWorkspacePage({
  params
}: {
  params: Promise<{ subjectId: string }>;
}) {
  const { subjectId } = await params;

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <ProtectedPage>
        <SubjectWorkspaceClient subjectId={Number(subjectId)} />
      </ProtectedPage>
    </main>
  );
}
