import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Layers, ArrowRight, Code2, Users, Zap } from "lucide-react";

export const metadata = {
  title: "Repox — Understand Any Codebase Instantly",
  description:
    "Upload a repository ZIP and get a beautiful, personalized explanation of every key part — built for founders, PMs, and devs alike.",
};

const features = [
  {
    icon: Sparkles,
    title: "AI-Powered Explanations",
    description:
      "Each file and module gets a plain-English explanation tailored to your technical level. Translate complex architecture into readable narratives.",
    delay: "delay-100",
    span: "md:col-span-2",
    gradient: "from-violet-400 to-violet-600",
  },
  {
    icon: Layers,
    title: "Architecture Map",
    description:
      "See how your codebase fits together — components, services, and models.",
    delay: "delay-200",
    span: "md:col-span-1",
    gradient: "from-cyan-400 to-cyan-600",
  },
  {
    icon: Users,
    title: "Three Audience Modes",
    description:
      "Beginner, Product, or Developer — pick your technical depth.",
    delay: "delay-300",
    span: "md:col-span-1",
    gradient: "from-pink-400 to-pink-600",
  },
  {
    icon: Zap,
    title: "Instant Results",
    description:
      "Drop a ZIP, answer two optional questions, and your interactive tour is ready in seconds. No complex config or local setup needed.",
    delay: "delay-400",
    span: "md:col-span-2",
    gradient: "from-emerald-400 to-emerald-600",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col bg-transparent text-clay-foreground select-none">
      {/* ── Nav ──────────────────────────────────────────────────── */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-black/5 bg-white/40 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-[#A78BFA] to-[#7C3AED] shadow-clay-button">
            <Code2 className="w-5 h-5 text-white" />
          </div>
          <span className="font-heading font-black text-xl text-clay-foreground tracking-tight">
            Repox
          </span>
        </div>
        <Link href="/upload">
          <Button
            size="sm"
            className="rounded-[16px] px-6 text-sm text-white"
          >
            Get Started
          </Button>
        </Link>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center relative overflow-hidden">


        {/* Headline */}
        <h1 className="animate-fade-up delay-100 font-heading font-black text-5xl sm:text-6xl md:text-7xl lg:text-8xl tracking-tight text-clay-foreground leading-[1.1] max-w-5xl mb-8">
          Understand any{" "}
          <span className="clay-text-gradient font-black">codebase</span>
          <br />
          without reading the code
        </h1>

        {/* Subtitle */}
        <p className="animate-fade-up delay-200 text-lg sm:text-xl max-w-2xl mb-12 leading-relaxed text-clay-muted font-sans font-medium">
          Drop a repository ZIP and Repox generates a personalized, visual
          explanation — for founders, product managers, and developers alike.
        </p>

        {/* CTA Buttons */}
        <div className="animate-fade-up delay-300 flex flex-col sm:flex-row gap-4 w-full sm:w-auto px-4">
          <Link href="/upload" className="w-full sm:w-auto">
            <Button
              id="cta-get-started"
              size="lg"
              className="w-full sm:w-auto rounded-[20px] px-8 text-base font-bold text-white shadow-clay-button hover:shadow-clay-button-hover"
            >
              Analyze a Repository
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>

        </div>

        {/* Floating code card */}
        <div className="animate-fade-up delay-400 animate-clay-float mt-20 rounded-[28px] border border-black/5 bg-white/70 backdrop-blur-xl px-8 py-6 text-left max-w-md w-full text-sm font-mono shadow-clay-card hover:-translate-y-3 hover:shadow-clay-card-hover transition-all duration-500">
          <div className="flex gap-2 mb-4">
            <span className="w-3.5 h-3.5 rounded-full bg-red-400 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.4)]" />
            <span className="w-3.5 h-3.5 rounded-full bg-yellow-400 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.4)]" />
            <span className="w-3.5 h-3.5 rounded-full bg-green-400 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.4)]" />
          </div>
          <div className="space-y-3">
            <div>
              <p className="flex items-center gap-1.5">
                <span className="text-clay-primary font-bold">✦</span>{" "}
                <span className="text-clay-foreground font-semibold">routes/upload.py</span>
              </p>
              <p className="pl-5 text-xs text-clay-muted leading-relaxed mt-1">
                Handles incoming ZIP uploads from the frontend, validates the file, extracts it, and stores metadata.
              </p>
            </div>
            <div className="pt-2 border-t border-black/5">
              <p className="flex items-center gap-1.5">
                <span className="text-clay-secondary font-bold">✦</span>{" "}
                <span className="text-clay-foreground font-semibold">services/inventory.py</span>
              </p>
              <p className="pl-5 text-xs text-clay-muted leading-relaxed mt-1">
                Walks the repo tree and classifies every file by language, category, and relevance.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features Bento Grid ──────────────────────────────────── */}
      <section className="px-6 pb-28">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-center font-heading font-black text-sm tracking-widest uppercase mb-16 text-clay-primary bg-clay-primary/5 rounded-full px-5 py-2 inline-block mx-auto left-1/2 relative -translate-x-1/2 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
            Everything you need
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {features.map(({ icon: Icon, title, description, delay, span, gradient }) => (
              <div
                key={title}
                className={`animate-fade-up ${delay} ${span} rounded-[32px] border border-black/5 bg-white/70 backdrop-blur-xl p-8 hover:-translate-y-2 hover:shadow-clay-card-hover hover:scale-[1.01] transition-all duration-300 shadow-clay-card flex flex-col`}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-6 shadow-clay-button bg-gradient-to-br ${gradient} text-white`}>
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-clay-foreground font-heading font-black text-xl mb-3">{title}</h3>
                <p className="text-clay-muted text-sm leading-relaxed font-sans font-medium">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer className="text-center text-xs font-sans font-semibold py-8 border-t border-black/5 bg-white/10 text-clay-muted">
        © 2026 Repox · Built for curious humans
      </footer>
    </main>
  );
}
