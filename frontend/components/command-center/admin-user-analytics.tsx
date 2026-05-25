"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Activity, Loader2, ShieldCheck, TrendingUp, Users } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getAdminUserAnalytics } from "@/lib/api";
import type { AdminAnalyticsBucket, AdminUserAnalytics } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type AnalyticsTab = "overview" | "growth" | "learners" | "learning";

const chartColors = ["hsl(var(--primary))", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316"];

export function AdminUserAnalyticsPanel() {
  const [analytics, setAnalytics] = useState<AdminUserAnalytics | null>(null);
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("overview");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadAnalytics() {
      try {
        const response = await getAdminUserAnalytics();
        if (isMounted) {
          setAnalytics(response);
        }
      } catch (caught) {
        if (isMounted) {
          setError(caught instanceof Error ? caught.message : "Unable to load user analytics.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadAnalytics();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-5 text-sm text-muted-foreground">
          <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
          Loading privacy-safe analytics...
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/40">
        <CardContent className="p-5 text-sm text-destructive">{error}</CardContent>
      </Card>
    );
  }

  if (!analytics) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">Analytics</p>
            <CardTitle>Abbot Command Center insights</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Aggregated charts only. Individual demographic details stay out of this view.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(["overview", "growth", "learners", "learning"] as AnalyticsTab[]).map((tab) => (
              <button
                key={tab}
                className={`rounded-full px-3 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab ? "bg-primary text-primary-foreground" : "border bg-background hover:bg-muted"
                }`}
                type="button"
                onClick={() => setActiveTab(tab)}
              >
                {friendlyLabel(tab)}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {activeTab === "overview" ? <OverviewCharts analytics={analytics} /> : null}
        {activeTab === "growth" ? <GrowthCharts analytics={analytics} /> : null}
        {activeTab === "learners" ? <LearnerCharts analytics={analytics} /> : null}
        {activeTab === "learning" ? <LearningCharts analytics={analytics} /> : null}

        <p className="flex gap-2 rounded-xl border bg-muted/40 p-3 text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          {analytics.privacy_note}
        </p>
      </CardContent>
    </Card>
  );
}

function OverviewCharts({ analytics }: { analytics: AdminUserAnalytics }) {
  return (
    <div className="space-y-5">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={<Users className="h-5 w-5" />} label="Active right now" value={analytics.currently_active_users} />
        <MetricCard icon={<Activity className="h-5 w-5" />} label="Daily active users" value={analytics.daily_active_users} />
        <MetricCard icon={<TrendingUp className="h-5 w-5" />} label="Weekly active users" value={analytics.weekly_active_users} />
        <MetricCard icon={<TrendingUp className="h-5 w-5" />} label="Monthly active users" value={analytics.monthly_active_users} />
      </section>
      <section className="grid gap-4 xl:grid-cols-2">
        <LineChartCard title="Signups over time" data={analytics.new_signups_over_time} lines={[{ key: "signups", name: "Signups" }]} />
        <BarChartCard title="Users by role" data={analytics.users_by_role} />
      </section>
    </div>
  );
}

function GrowthCharts({ analytics }: { analytics: AdminUserAnalytics }) {
  return (
    <section className="grid gap-4 xl:grid-cols-2">
      <AreaChartCard title="Textbook uploads over time" data={analytics.textbook_uploads_over_time} dataKey="uploads" />
      <AreaChartCard title="Concept completions over time" data={analytics.concept_completions_over_time} dataKey="completions" />
      <LineChartCard title="Quiz pass/fail trends" data={analytics.quiz_pass_fail_trends} lines={[{ key: "passed", name: "Passed" }, { key: "failed", name: "Failed" }]} />
      <BarChartCard title="Most active subjects" data={analytics.most_active_subjects} />
    </section>
  );
}

function LearnerCharts({ analytics }: { analytics: AdminUserAnalytics }) {
  return (
    <section className="grid gap-4 xl:grid-cols-2">
      <BarChartCard title="Users by country" data={analytics.users_by_country} />
      <PieChartCard title="Users by age range" data={analytics.users_by_age_range} />
      <PieChartCard title="Users by gender" data={analytics.users_by_gender} />
      <BarChartCard title="Users by education level" data={analytics.users_by_education_level} />
    </section>
  );
}

function LearningCharts({ analytics }: { analytics: AdminUserAnalytics }) {
  return (
    <div className="space-y-5">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={<Users className="h-5 w-5" />} label="Total users" value={analytics.total_users} />
        <MetricCard icon={<Activity className="h-5 w-5" />} label="Logged in today" value={analytics.users_logged_in_today} />
        <MetricCard icon={<TrendingUp className="h-5 w-5" />} label="Avg textbooks/user" value={analytics.average_textbooks_per_user} />
        <MetricCard icon={<TrendingUp className="h-5 w-5" />} label="Avg concepts done/user" value={analytics.average_concepts_completed_per_user} />
      </section>
      <section className="grid gap-4 xl:grid-cols-2">
        <LineChartCard title="Quiz pass/fail trends" data={analytics.quiz_pass_fail_trends} lines={[{ key: "passed", name: "Passed" }, { key: "failed", name: "Failed" }, { key: "total", name: "Total" }]} />
        <AreaChartCard title="Concept completions over time" data={analytics.concept_completions_over_time} dataKey="completions" />
      </section>
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-xl border bg-background p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">{icon}</div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-semibold">{value.toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}

function ChartFrame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border bg-background p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-4 h-72">{children}</div>
    </div>
  );
}

function LineChartCard({ title, data, lines }: { title: string; data: Array<Record<string, string | number>>; lines: Array<{ key: string; name: string }> }) {
  return (
    <ChartFrame title={title}>
      {data.length === 0 ? <EmptyChart /> : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            {lines.map((line, index) => (
              <Line key={line.key} type="monotone" dataKey={line.key} name={line.name} stroke={chartColors[index % chartColors.length]} strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartFrame>
  );
}

function AreaChartCard({ title, data, dataKey }: { title: string; data: Array<Record<string, string | number>>; dataKey: string }) {
  return (
    <ChartFrame title={title}>
      {data.length === 0 ? <EmptyChart /> : (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Area type="monotone" dataKey={dataKey} stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.18} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </ChartFrame>
  );
}

function BarChartCard({ title, data }: { title: string; data: AdminAnalyticsBucket[] }) {
  return (
    <ChartFrame title={title}>
      {data.length === 0 ? <EmptyChart /> : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.map((row) => ({ ...row, label: friendlyLabel(row.label) }))}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} angle={-20} textAnchor="end" height={70} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="value" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartFrame>
  );
}

function PieChartCard({ title, data }: { title: string; data: AdminAnalyticsBucket[] }) {
  return (
    <ChartFrame title={title}>
      {data.length === 0 ? <EmptyChart /> : (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data.map((row) => ({ ...row, label: friendlyLabel(row.label) }))} dataKey="value" nameKey="label" outerRadius={95} label>
              {data.map((row, index) => (
                <Cell key={row.label} fill={chartColors[index % chartColors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      )}
    </ChartFrame>
  );
}

function EmptyChart() {
  return <div className="flex h-full items-center justify-center rounded-lg bg-muted/40 text-sm text-muted-foreground">No aggregate data yet.</div>;
}

function friendlyLabel(value: string): string {
  return value.replaceAll("_", " ");
}
