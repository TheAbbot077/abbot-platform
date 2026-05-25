import { ProtectedPage } from "@/components/auth/protected-page";
import { DashboardClient } from "@/components/dashboard/dashboard-client";

export default function DashboardPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <ProtectedPage>
        <>
          <div className="mb-6">
            <div>
              <p className="text-sm font-medium text-primary">Home</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal">Ready for one small win?</h1>
              <p className="mt-2 max-w-2xl text-sm text-muted-foreground">A calm launchpad for your subjects, The Abbot, Ariel, and today’s next step.</p>
            </div>
          </div>
          <DashboardClient />
        </>
      </ProtectedPage>
    </main>
  );
}
