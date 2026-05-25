import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-[#0b2d68] via-white to-white px-4 py-10 text-slate-950 sm:px-6 lg:px-8">
      <article className="mx-auto max-w-3xl rounded-3xl border border-white/70 bg-white/90 p-6 shadow-xl backdrop-blur md:p-8">
        <Link className="text-sm font-semibold text-[#0b2d68]" href="/">
          Back to Abbot Study
        </Link>
        <h1 className="mt-6 text-3xl font-semibold tracking-normal">Privacy Policy</h1>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          This beta privacy notice explains what Abbot Study collects during testing and how we use it. It should be reviewed by legal counsel before a public production launch.
        </p>

        <section className="mt-8 space-y-4 text-sm leading-7 text-slate-700">
          <h2 className="text-xl font-semibold text-slate-950">What we collect</h2>
          <p>
            We collect account details, learning profile information, uploaded study materials, study progress, quiz attempts, tutor interactions, and technical usage data needed to operate and improve the product.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">How we use it</h2>
          <p>
            We use this information to provide ordered learning paths, tutor explanations, progress tracking, Ariel memory features, security, analytics, and beta product improvement.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Beta analytics</h2>
          <p>
            Optional demographic fields are used in aggregate to understand who the beta serves. We avoid exposing sensitive individual profile details in normal admin analytics views.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Uploaded materials</h2>
          <p>
            Uploaded PDFs are used to create learning content for the account that uploaded them. Students should only upload materials they are allowed to use for study.
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Contact</h2>
          <p>
            During beta, privacy requests should be handled by the product owner through the official support channel configured before launch.
          </p>
        </section>
      </article>
    </main>
  );
}
