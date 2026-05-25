import Link from "next/link";

import { Button } from "@/components/ui/button";

const feedbackUrl = process.env.NEXT_PUBLIC_BETA_FEEDBACK_URL;

export default function BetaFeedbackPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-[#0b2d68] via-white to-white px-4 py-10 text-slate-950 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-3xl rounded-3xl border border-white/70 bg-white/90 p-6 shadow-xl backdrop-blur md:p-8">
        <Link className="text-sm font-semibold text-[#0b2d68]" href="/">
          Back to Abbot Study
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-normal">Beta Feedback</h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          Help us make Abbot Study clearer, friendlier, and more useful before launch.
        </p>

        {feedbackUrl ? (
          <form action={feedbackUrl} method="post" className="mt-8 space-y-5">
            <label className="block">
              <span className="text-sm font-semibold text-slate-800">Name</span>
              <input name="name" className="mt-2 min-h-12 w-full rounded-2xl border border-blue-100 bg-white px-4 text-base outline-none ring-[#f5c542] focus:ring-2" />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-slate-800">Email</span>
              <input name="email" type="email" className="mt-2 min-h-12 w-full rounded-2xl border border-blue-100 bg-white px-4 text-base outline-none ring-[#f5c542] focus:ring-2" />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-slate-800">What were you testing?</span>
              <select name="area" className="mt-2 min-h-12 w-full rounded-2xl border border-blue-100 bg-white px-4 text-base outline-none ring-[#f5c542] focus:ring-2">
                <option>Signup or login</option>
                <option>Textbook upload</option>
                <option>The Abbot lesson</option>
                <option>MCQs or progress</option>
                <option>Ariel</option>
                <option>Mobile experience</option>
                <option>Other</option>
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-slate-800">Feedback</span>
              <textarea name="feedback" required rows={6} className="mt-2 w-full rounded-2xl border border-blue-100 bg-white px-4 py-3 text-base outline-none ring-[#f5c542] focus:ring-2" />
            </label>
            <Button type="submit" className="min-h-12 w-full bg-[#f5c542] text-slate-950 hover:bg-[#ffd76a] sm:w-auto">
              Send feedback
            </Button>
          </form>
        ) : (
          <div className="mt-8 rounded-3xl border border-amber-200 bg-amber-50 p-5 text-sm leading-7 text-amber-950">
            Feedback collection is ready, but `NEXT_PUBLIC_BETA_FEEDBACK_URL` is not configured yet. Add a trusted form endpoint before inviting beta users.
          </div>
        )}
      </section>
    </main>
  );
}
