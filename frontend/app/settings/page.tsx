import Link from "next/link";

import { ProtectedPage } from "@/components/auth/protected-page";
import { SettingsClient } from "@/components/settings/settings-client";

export default function SettingsPage() {
  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <ProtectedPage>
        <>
          <div className="mb-6">
            <Link className="text-sm font-medium text-primary" href="/dashboard">Back to dashboard</Link>
            <h1 className="mt-2 text-2xl font-semibold tracking-normal">Account settings</h1>
          </div>
          <SettingsClient />
        </>
      </ProtectedPage>
    </main>
  );
}
