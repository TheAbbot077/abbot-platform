import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-[#0b2d68] via-white to-white px-4 py-10 text-slate-950 sm:px-6 lg:px-8">
      <article className="mx-auto max-w-3xl rounded-3xl border border-white/70 bg-white/90 p-6 shadow-xl backdrop-blur md:p-8">
        <Link className="text-sm font-semibold text-[#0b2d68]" href="/">
          Back to Abbot Study
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-normal">Terms of Use</h1>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          These beta terms describe expected use of Abbot Study during testing. They should be reviewed by legal counsel before public production launch.
        </p>

        <section className="mt-8 space-y-4 text-sm leading-7 text-slate-700">
          <h2 className="text-xl font-semibold text-slate-950">Beta product</h2>
          <p>
            Abbot Study is being tested and may change. Features can be added, removed, or adjusted as we learn from beta users.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Study support</h2>
          <p>
            The Abbot and Ariel are learning tools. Students should verify important answers with teachers, approved textbooks, or trusted sources.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">User responsibilities</h2>
          <p>
            Users should provide accurate account information, protect their login details, and upload only study materials they have the right to use.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Acceptable use</h2>
          <p>
            Users may not attempt to access another user’s data, bypass security controls, overload the service, or use the platform for unlawful purposes.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Beta feedback</h2>
          <p>
            Feedback shared during beta may be used to improve the product, prioritize fixes, and guide future learning features.
          </p>
        </section>
      </article>
    </main>
  );
}
