import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  GraduationCap,
  Layers3,
  LineChart,
  MessageCircle,
  Sparkles
} from "lucide-react";

import { PublicSessionInvalidator } from "@/components/auth/public-session-invalidator";
import { Button } from "@/components/ui/button";

const features = [
  {
    title: "Upload your textbook",
    body: "Turn PDFs, notes, and chapters into a clean learning path.",
    icon: BookOpen
  },
  {
    title: "Learn with The Abbot",
    body: "Study one concept at a time with a patient AI guide.",
    icon: GraduationCap
  },
  {
    title: "Practice with smart concept checks",
    body: "Answer focused questions before moving forward.",
    icon: CheckCircle2
  },
  {
    title: "Teach Ariel",
    body: "Explain what you learned to prove true mastery.",
    icon: BrainCircuit
  },
  {
    title: "Track your mastery",
    body: "See progress, weak spots, and rescue missions clearly.",
    icon: LineChart
  }
];

const steps = [
  "Create a subject workspace.",
  "Upload a textbook or notes.",
  "Follow chapters and concepts in order.",
  "Practice, reteach, and reinforce."
];

const reasons = [
  {
    title: "Order stays protected",
    body: "The system respects chapter and concept sequence instead of async processing order.",
    icon: Layers3
  },
  {
    title: "Teaching becomes active",
    body: "The Abbot explains, checks understanding, and lets students ask follow-up questions.",
    icon: MessageCircle
  },
  {
    title: "Mastery is visible",
    body: "Ariel, Bloom levels, and reinforcement alerts make weak spots easier to fix.",
    icon: Sparkles
  }
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white text-slate-950">
      <PublicSessionInvalidator />
      <section className="relative isolate min-h-screen overflow-hidden bg-[#0b2d68]">
        <HeroImageBackdrop />
        <div className="absolute inset-0 bg-gradient-to-r from-[#061a3f] via-[#0b2d68]/88 to-[#0b2d68]/28" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_20%,rgba(245,197,66,0.34),transparent_28rem)]" />

        <PublicNav />

        <div className="relative z-10 mx-auto grid min-h-screen w-full max-w-7xl items-center gap-10 px-4 pb-14 pt-28 sm:px-6 lg:grid-cols-[1.02fr_0.98fr] lg:px-8">
          <div className="max-w-3xl py-10 text-white">
            <p className="inline-flex rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium text-[#ffe39b] backdrop-blur">
              AI-powered study paths for serious students
            </p>
            <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-tight tracking-normal sm:text-5xl lg:text-6xl">
              Master every subject with The Abbot.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-blue-50 sm:text-lg">
              Upload your textbook, follow a guided learning path, learn each concept step by step, and teach Ariel to prove true mastery.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild className="h-12 bg-[#f5c542] px-6 text-base text-slate-950 hover:bg-[#ffd76a]">
                <Link href="/signup">
                  Start studying
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-12 border-white/35 bg-white/10 px-6 text-base text-white hover:bg-white/20">
                <Link href="/login">Log in</Link>
              </Button>
            </div>
          </div>

          <div className="relative min-h-[28rem] items-end justify-center sm:flex lg:min-h-[34rem]">
            <HeroImagePanel />
          </div>
        </div>
      </section>

      <section className="bg-[#f8fafc] px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <SectionIntro eyebrow="How it works" title="A focused study loop, built for momentum." />
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step, index) => (
              <article key={step} className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#0b2d68] text-sm font-semibold text-[#ffe39b]">
                  {index + 1}
                </div>
                <h3 className="mt-4 text-base font-semibold text-slate-950">{step}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {index === 0 ? "Keep each class, exam, or book in its own calm workspace." : null}
                  {index === 1 ? "The Abbot prepares ordered chapters and learnable concepts." : null}
                  {index === 2 ? "Students move forward only when the current concept is ready." : null}
                  {index === 3 ? "Ariel helps turn review into a playful teach-back habit." : null}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <SectionIntro eyebrow="Why it works" title="Built around sequence, retrieval, and teach-back." />
          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {reasons.map((reason) => {
              const Icon = reason.icon;
              return (
                <article key={reason.title} className="rounded-3xl border border-blue-100 bg-[#f8fafc] p-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f5c542] text-slate-950">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold text-slate-950">{reason.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{reason.body}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-[#f8fafc] px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <SectionIntro eyebrow="Feature highlights" title="Everything a study session needs, without the clutter." />
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <article key={feature.title} className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#0b2d68] text-[#ffe39b]">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-slate-950">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{feature.body}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-[#0b2d68] px-4 py-16 text-white sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 rounded-3xl border border-white/15 bg-white/10 p-6 shadow-2xl shadow-blue-950/20 backdrop-blur md:flex-row md:items-center md:justify-between md:p-8">
          <div>
            <AbookLogo tone="dark" />
            <h2 className="mt-6 max-w-2xl text-3xl font-semibold tracking-normal">Ready to make your next textbook less overwhelming?</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-blue-50">Start with one subject, one textbook, and one concept. The Abbot will keep the path clear.</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild className="h-12 bg-[#f5c542] px-6 text-slate-950 hover:bg-[#ffd76a]">
              <Link href="/signup">Create account</Link>
            </Button>
            <Button asChild variant="outline" className="h-12 border-white/35 bg-white/10 px-6 text-white hover:bg-white/20">
              <Link href="/login">Log in</Link>
            </Button>
          </div>
        </div>
      </section>

      <footer className="border-t border-blue-100 bg-white px-4 py-8 text-sm text-slate-600 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Abbot Study. Built for careful beta testing.</p>
          <nav className="flex flex-wrap gap-4" aria-label="Footer navigation">
            <Link className="font-medium text-[#0b2d68]" href="/privacy">Privacy</Link>
            <Link className="font-medium text-[#0b2d68]" href="/terms">Terms</Link>
            <Link className="font-medium text-[#0b2d68]" href="/beta-feedback">Beta feedback</Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}

function PublicNav() {
  return (
    <header className="absolute inset-x-0 top-0 z-20">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
        <AbookLogo tone="dark" />
        <nav className="flex items-center gap-2" aria-label="Public navigation">
          <Button asChild variant="outline" size="sm" className="border-white/35 bg-white/10 text-white hover:bg-white/20">
            <Link href="/login">Log in</Link>
          </Button>
          <Button asChild size="sm" className="bg-[#f5c542] text-slate-950 hover:bg-[#ffd76a]">
            <Link href="/signup">Sign up</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}

function SectionIntro({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-semibold text-[#c7961a]">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">{title}</h2>
    </div>
  );
}

function AbookLogo({ tone }: { tone: "dark" | "light" }) {
  const isDark = tone === "dark";
  return (
    <Link className="inline-flex items-center gap-3" href="/" aria-label="Abbot Study home">
      <span className={`relative flex h-14 w-14 items-center justify-center rounded-2xl border shadow-xl ${isDark ? "border-white/20 bg-white text-[#0b2d68] shadow-black/20" : "border-blue-100 bg-[#0b2d68] text-white shadow-blue-950/10"}`}>
        <svg viewBox="0 0 64 64" className="h-11 w-11" aria-hidden="true">
          <path d="M10 43c8-6 16-6 22 0 6-6 14-6 22 0v8c-8-4-15-4-22 1-7-5-14-5-22-1z" fill="#f5c542" />
          <path d="M22 40 32 16l10 24h-6l-2-5h-8l-2 5zM28 30h8l-4-10z" fill={isDark ? "#0b2d68" : "#ffffff"} />
          <path d="M18 14h28l-14-6z" fill="#111827" />
          <path d="M46 14v9" stroke="#f5c542" strokeWidth="3" strokeLinecap="round" />
          <circle cx="46" cy="25" r="3" fill="#f5c542" />
        </svg>
      </span>
      <span>
        <span className={`block text-xl font-semibold tracking-normal ${isDark ? "text-white" : "text-slate-950"}`}>Abbot Study</span>
        <span className={`block text-xs font-medium uppercase ${isDark ? "text-[#ffe39b]" : "text-[#c7961a]"}`}>The Abbot and Ariel</span>
      </span>
    </Link>
  );
}

function HeroImageBackdrop() {
  return (
    <div className="absolute inset-0">
      <img
        src="/images/hero-graduation-scene.jpg"
        alt=""
        className="h-full w-full object-cover object-[58%_50%]"
        aria-hidden="true"
      />
      <div className="absolute inset-0 bg-[#061a3f]/25" />
    </div>
  );
}

function HeroImagePanel() {
  return (
    <div className="relative mx-auto h-[28rem] w-full max-w-xl lg:h-[31rem]">
      <div className="absolute inset-0 rounded-[2rem] border border-white/20 bg-white/10 p-3 shadow-2xl shadow-blue-950/35 backdrop-blur-sm">
        <img
          src="/images/hero-graduation-scene.jpg"
          alt="A black graduation cap with a gold tassel resting on stacked books in a library."
          className="h-full w-full rounded-[1.35rem] object-cover object-center"
        />
      </div>
      <div className="absolute bottom-5 left-1/2 w-[calc(100%-2.5rem)] -translate-x-1/2 rounded-3xl border border-white/20 bg-[#061a3f]/70 p-4 text-center text-sm text-white shadow-xl backdrop-blur">
        <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-[#f5c542] text-slate-950">
          <Sparkles className="h-5 w-5" aria-hidden="true" />
        </div>
        Give me a place to stand and I shall move the world - Archimedes
      </div>
    </div>
  );
}
