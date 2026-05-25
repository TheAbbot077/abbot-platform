import { ProtectedPage } from "@/components/auth/protected-page";
import { SubjectsClient } from "@/components/subjects/subjects-client";

export default function SubjectsPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <ProtectedPage>
        <>
          <div className="mb-6">
            <p className="text-sm font-medium text-primary">Subjects</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal">Choose your study space</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Pick one subject first, then study its textbooks, concepts, The Abbot lessons, Ariel practice, and progress in one focused place.
            </p>
          </div>
          <SubjectsClient />
        </>
      </ProtectedPage>
    </main>
  );
}
