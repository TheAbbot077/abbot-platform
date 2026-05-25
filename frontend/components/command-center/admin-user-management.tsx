"use client";

import { useEffect, useState } from "react";
import { Loader2, Search, ShieldCheck, UserRoundCheck, UserRoundX } from "lucide-react";

import { getAdminUserDetail, getAdminUsers, setAdminUserActive } from "@/lib/api";
import type { AdminUserDetail, AdminUserListItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type UserStatusFilter = "all" | "active" | "inactive";
type UserRoleFilter = "all" | "staff" | "non_staff" | "superuser";

export function AdminUserManagement() {
  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<UserStatusFilter>("all");
  const [roleFilter, setRoleFilter] = useState<UserRoleFilter>("all");
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadUsers() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getAdminUsers({ q: query, status: statusFilter, role: roleFilter });
      setUsers(response.users);
      setTotalCount(response.total_count);
      if (selectedUser) {
        const stillVisible = response.users.some((user) => user.id === selectedUser.id);
        if (!stillVisible) {
          setSelectedUser(null);
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load users.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadUsers();
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [query, statusFilter, roleFilter]);

  async function loadUserDetail(userId: number) {
    setError(null);
    try {
      setSelectedUser(await getAdminUserDetail(userId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load user profile.");
    }
  }

  async function toggleUserActive(user: AdminUserDetail) {
    const nextIsActive = !user.is_active;
    const confirmed = window.confirm(`${nextIsActive ? "Reactivate" : "Deactivate"} ${user.username}?`);
    if (!confirmed) {
      return;
    }

    setIsUpdating(true);
    setError(null);
    try {
      const updatedUser = await setAdminUserActive(user.id, nextIsActive);
      setSelectedUser(updatedUser);
      await loadUsers();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update user.");
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>User management</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Search students and admins, inspect learning activity, and manage account access.</p>
          </div>
          <div className="text-sm text-muted-foreground">{totalCount.toLocaleString()} users found</div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 lg:grid-cols-[1fr_160px_170px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              className="h-11 w-full rounded-xl border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search username or email"
            />
          </label>
          <select
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as UserStatusFilter)}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <select
            className="h-11 rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
            value={roleFilter}
            onChange={(event) => setRoleFilter(event.target.value as UserRoleFilter)}
          >
            <option value="all">All roles</option>
            <option value="staff">Staff</option>
            <option value="non_staff">Students</option>
            <option value="superuser">Superusers</option>
          </select>
        </div>

        {error ? <p className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p> : null}

        <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-3 font-semibold">User</th>
                  <th className="px-3 py-3 font-semibold">Role</th>
                  <th className="px-3 py-3 font-semibold">Status</th>
                  <th className="px-3 py-3 font-semibold">Textbooks</th>
                  <th className="px-3 py-3 font-semibold">Attempts</th>
                  <th className="px-3 py-3 font-semibold">Joined</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={6}>
                      <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
                      Loading users...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={6}>
                      No users match these filters.
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr
                      key={user.id}
                      className={`cursor-pointer border-t transition-colors hover:bg-muted/50 ${selectedUser?.id === user.id ? "bg-muted/60" : ""}`}
                      onClick={() => void loadUserDetail(user.id)}
                    >
                      <td className="px-3 py-3">
                        <p className="font-medium">{user.username}</p>
                        <p className="text-xs text-muted-foreground">{user.email || "No email"}</p>
                      </td>
                      <td className="px-3 py-3">{roleLabel(user)}</td>
                      <td className="px-3 py-3">{user.is_active ? "Active" : "Inactive"}</td>
                      <td className="px-3 py-3">{user.document_count}</td>
                      <td className="px-3 py-3">{user.quiz_attempt_count}</td>
                      <td className="px-3 py-3">{formatDate(user.date_joined)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <UserDetailPanel user={selectedUser} isUpdating={isUpdating} onToggleActive={toggleUserActive} />
        </div>
      </CardContent>
    </Card>
  );
}

function UserDetailPanel({
  user,
  isUpdating,
  onToggleActive,
}: {
  user: AdminUserDetail | null;
  isUpdating: boolean;
  onToggleActive: (user: AdminUserDetail) => void;
}) {
  if (!user) {
    return (
      <div className="rounded-xl border bg-background p-5 text-sm text-muted-foreground">
        Select a user to view subjects, textbooks, and learning progress.
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl border bg-background p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-lg font-semibold">{user.username}</p>
          <p className="text-sm text-muted-foreground">{user.email || "No email"}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {roleLabel(user)} - {user.is_active ? "Active" : "Inactive"}
          </p>
        </div>
        <Button type="button" variant={user.is_active ? "outline" : "secondary"} onClick={() => onToggleActive(user)} disabled={isUpdating}>
          {user.is_active ? <UserRoundX className="h-4 w-4" aria-hidden="true" /> : <UserRoundCheck className="h-4 w-4" aria-hidden="true" />}
          {user.is_active ? "Deactivate" : "Reactivate"}
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <MiniStat label="Subjects" value={user.summary.subject_count} />
        <MiniStat label="Textbooks" value={user.summary.document_count} />
        <MiniStat label="Ready" value={user.summary.ready_document_count} />
        <MiniStat label="Failed" value={user.summary.failed_document_count} />
        <MiniStat label="Attempts" value={user.summary.quiz_attempt_count} />
        <MiniStat label="The Abbot" value={user.summary.tutor_session_count} />
      </div>

      <section>
        <h3 className="text-sm font-semibold">Learning progress</h3>
        <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
          <MiniStat label="Passed" value={user.learning_progress.passed} />
          <MiniStat label="In progress" value={user.learning_progress.in_progress} />
          <MiniStat label="Available" value={user.learning_progress.available} />
          <MiniStat label="Locked" value={user.learning_progress.locked} />
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold">Subjects</h3>
        <div className="mt-2 space-y-2">
          {user.subjects.length === 0 ? (
            <p className="text-sm text-muted-foreground">No subjects yet.</p>
          ) : (
            user.subjects.map((subject) => (
              <div key={subject.id} className="flex justify-between rounded-lg bg-muted/40 px-3 py-2 text-sm">
                <span>{subject.name}</span>
                <span className="text-muted-foreground">{subject.document_count} textbooks</span>
              </div>
            ))
          )}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold">Recent textbooks</h3>
        <div className="mt-2 space-y-2">
          {user.textbooks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No textbooks uploaded yet.</p>
          ) : (
            user.textbooks.slice(0, 5).map((textbook) => (
              <div key={textbook.id} className="rounded-lg bg-muted/40 px-3 py-2 text-sm">
                <p className="font-medium">{textbook.title}</p>
                <p className="text-xs text-muted-foreground">
                  {textbook.subject_name ?? "No subject"} - {textbook.status.replaceAll("_", " ")}
                </p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value.toLocaleString()}</p>
    </div>
  );
}

function roleLabel(user: Pick<AdminUserListItem, "is_superuser" | "is_staff">): string {
  if (user.is_superuser) {
    return "Superuser";
  }
  if (user.is_staff) {
    return "Staff";
  }
  return "Student";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
