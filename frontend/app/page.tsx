import Link from "next/link";
import { Button } from "@/components/ui/button";
import { GitBranch, Sparkles, Layers, ArrowRight, Code2, Users, Zap } from "lucide-react";

export const metadata = {
  title: "RepoTutor — Understand Any Codebase Instantly",
  description:
    "Upload a repository ZIP and get a beautiful, personalized explanation of every key part — built for founders, PMs, and devs alike.",
};

const features = [
  {
    icon: Sparkles,
    title: "AI-Powered Explanations",
    description:
      "Each file and module gets a plain-English explanation tailored to your technical level.",
    delay: "delay-100",
  },
  {
    icon: Layers,
    title: "Visual Architecture Map",
    description:
      "See how your codebase fits together — components, services, data models — at a glance.",
    delay: "delay-200",
  },
  {
    icon: Users,
    title: "Three Audience Modes",
    description:
      "Beginner, Product, or Developer — pick your depth and get explanations that match.",
    delay: "delay-300",
  },
  {
    icon: Zap,
    title: "Instant Results",
    description:
      "Drop a ZIP, answer two optional questions, and your interactive tour is ready in seconds.",
    delay: "delay-400",
  },
];

export default function HomePage() {
  return (
    <main
      className="min-h-screen flex flex-col"
      style={{ background: "var(--surface-1)", color: "var(--foreground)" }}
    >
      {/* ── Nav ──────────────────────────────────────────────────── */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "var(--brand)" }}
          >
            <Code2 className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-white tracking-tight text-lg">RepoTutor</span>
        </div>
        <Link href="/upload">
          <Button
            size="sm"
            className="rounded-full px-5 text-white border border-white/10"
            style={{ background: "var(--brand)" }}
          >
            Get Started
          </Button>
        </Link>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center relative overflow-hidden">
        {/* Glow blobs */}
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse, oklch(0.6 0.24 285 / 12%) 0%, transparent 70%)",
          }}
        />
        <div
          className="absolute bottom-10 right-1/4 w-72 h-72 rounded-full pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse, oklch(0.6 0.2 220 / 10%) 0%, transparent 70%)",
          }}
        />

        {/* Badge */}
        <div
          className="animate-fade-up inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium mb-6 border"
          style={{
            background: "var(--brand-dim)",
            borderColor: "oklch(0.6 0.24 285 / 30%)",
            color: "oklch(0.8 0.18 285)",
          }}
        >
          <Sparkles className="w-3 h-3" />
          AI-powered codebase tours
        </div>

        {/* Headline */}
        <h1 className="animate-fade-up delay-100 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-white leading-[1.1] max-w-4xl mb-6">
          Understand any{" "}
          <span className="text-gradient">codebase</span>
          <br />
          without reading the code
        </h1>

        {/* Sub */}
        <p
          className="animate-fade-up delay-200 text-lg sm:text-xl max-w-xl mb-10 leading-relaxed"
          style={{ color: "oklch(0.65 0.02 280)" }}
        >
          Drop a repository ZIP and RepoTutor generates a personalized, visual
          explanation — for founders, PMs, and developers alike.
        </p>

        {/* CTA */}
        <div className="animate-fade-up delay-300 flex flex-col sm:flex-row gap-3">
          <Link href="/upload">
            <Button
              id="cta-get-started"
              size="lg"
              className="rounded-full px-8 h-12 text-base font-semibold text-white animate-glow-pulse"
              style={{ background: "var(--brand)" }}
            >
              Analyze a Repository
              <ArrowRight className="ml-2 w-4 h-4" />
            </Button>
          </Link>
          <Button
            variant="outline"
            size="lg"
            className="rounded-full px-8 h-12 text-base border-white/10 text-white/70 hover:text-white hover:bg-white/5"
          >
            <GitBranch className="mr-2 w-4 h-4" />
            See an example
          </Button>
        </div>

        {/* Floating code card */}
        <div
          className="animate-fade-up delay-400 animate-float mt-16 rounded-2xl border border-white/10 px-6 py-4 text-left max-w-md w-full text-sm font-mono"
          style={{
            background: "var(--surface-2)",
            color: "oklch(0.7 0.05 280)",
            boxShadow: "0 0 60px oklch(0.6 0.24 285 / 10%)",
          }}
        >
          <div className="flex gap-1.5 mb-3">
            <span className="w-3 h-3 rounded-full bg-red-500/70" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
            <span className="w-3 h-3 rounded-full bg-green-500/70" />
          </div>
          <div className="space-y-1">
            <p>
              <span style={{ color: "oklch(0.6 0.24 285)" }}>✦</span>{" "}
              <span className="text-white/80">routes/upload.py</span>
            </p>
            <p className="pl-4 text-xs" style={{ color: "oklch(0.6 0.05 280)" }}>
              Handles incoming ZIP uploads from the frontend, validates the
              file, extracts it, and stores project metadata.
            </p>
            <p className="mt-2">
              <span style={{ color: "oklch(0.72 0.2 220)" }}>✦</span>{" "}
              <span className="text-white/80">services/inventory.py</span>
            </p>
            <p className="pl-4 text-xs" style={{ color: "oklch(0.6 0.05 280)" }}>
              Walks the repo tree and classifies every file by language,
              category, and relevance.
            </p>
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────── */}
      <section className="px-6 pb-24">
        <div className="max-w-5xl mx-auto">
          <h2
            className="text-center text-sm font-semibold tracking-widest uppercase mb-12"
            style={{ color: "oklch(0.55 0.05 280)" }}
          >
            Everything you need
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map(({ icon: Icon, title, description, delay }) => (
              <div
                key={title}
                className={`animate-fade-up ${delay} rounded-2xl border border-white/5 p-6 hover:border-white/10 transition-colors group`}
                style={{ background: "var(--surface-2)" }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
                  style={{ background: "var(--brand-dim)" }}
                >
                  <Icon className="w-5 h-5" style={{ color: "var(--brand)" }} />
                </div>
                <h3 className="text-white font-semibold mb-2 text-sm">{title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: "oklch(0.55 0.02 280)" }}>
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer
        className="text-center text-xs py-6 border-t border-white/5"
        style={{ color: "oklch(0.4 0.01 280)" }}
      >
        © 2026 RepoTutor · Built for curious humans
      </footer>
    </main>
  );
}
