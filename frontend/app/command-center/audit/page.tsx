import Link from "next/link";

import { StaffPage } from "@/components/auth/staff-page";
import { AdminAuditLogPanel } from "@/components/command-center/admin-audit-log";

export default function CommandCenterAuditPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <StaffPage>
        <>
          <div className="mb-6">
            <Link className="text-sm font-medium text-primary hover:underline" href="/command-center">
              Back to Abbot Command Center
            </Link>
            <h1 className="mt-3 text-3xl font-semibold tracking-normal">Admin audit log</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Trace sensitive admin actions, quality-tool changes, textbook reprocessing, deletes, and restarts.
            </p>
          </div>
          <AdminAuditLogPanel />
        </>
      </StaffPage>
    </main>
  );
}
