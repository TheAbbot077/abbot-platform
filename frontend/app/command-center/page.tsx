import { StaffPage } from "@/components/auth/staff-page";
import { CommandCenterClient } from "@/components/command-center/command-center-client";

export default function CommandCenterPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <StaffPage>
        <>
          <div className="mb-6">
            <p className="text-sm font-medium text-primary">Privileged admin view</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal">Abbot Command Center</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Monitor platform health, textbook processing, parser confidence, and learning activity across the app.
            </p>
          </div>
          <CommandCenterClient />
        </>
      </StaffPage>
    </main>
  );
}
