"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone, FileRejection } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";
import {
  Upload,
  FileArchive,
  X,
  AlertCircle,
  Loader2,
  Code2,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

type TechnicalLevel = "beginner" | "product" | "developer";

const levels: { value: TechnicalLevel; label: string; description: string }[] = [
  {
    value: "beginner",
    label: "Beginner",
    description: "Plain English, no jargon — perfect if you're non-technical.",
  },
  {
    value: "product",
    label: "Product / Semi-Technical",
    description: "You know how software works but don't write code every day.",
  },
  {
    value: "developer",
    label: "Developer",
    description: "Full technical depth: patterns, trade-offs, and implementation details.",
  },
];

export default function UploadPage() {
  const router = useRouter();

  // Form state
  const [file, setFile] = useState<File | null>(null);
  const [productDescription, setProductDescription] = useState("");
  const [importantFeatures, setImportantFeatures] = useState("");
  const [technicalLevel, setTechnicalLevel] = useState<TechnicalLevel>("beginner");

  // UI state
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // ── Dropzone ─────────────────────────────────────────────────
  const onDrop = useCallback((accepted: File[], rejected: FileRejection[]) => {
    setError(null);
    if (rejected.length > 0) {
      setError("Only .zip files are accepted. Please choose a valid ZIP archive.");
      return;
    }
    if (accepted.length > 0) {
      setFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/zip": [".zip"] },
    maxFiles: 1,
    multiple: false,
  });

  // ── Submit ────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a ZIP file before submitting.");
      return;
    }

    setError(null);
    setUploading(true);
    setProgress(10);

    const formData = new FormData();
    formData.append("file", file);
    if (productDescription.trim()) formData.append("product_description", productDescription);
    if (importantFeatures.trim()) formData.append("important_features", importantFeatures);
    formData.append("technical_level", technicalLevel);

    // Animate progress while uploading
    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 8, 85));
    }, 300);

    try {
      const res = await fetch(`${API_URL}/api/projects`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg =
          data?.detail?.message ?? data?.detail ?? "Upload failed. Please try again.";
        throw new Error(msg);
      }

      const data = await res.json();
      setProgress(100);

      // Brief pause so the user sees 100% before redirect
      await new Promise((r) => setTimeout(r, 400));
      router.push(`/analyze/${data.project_id}`);
    } catch (err: unknown) {
      clearInterval(progressInterval);
      setProgress(0);
      setUploading(false);
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  // ── Helpers ───────────────────────────────────────────────────
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--surface-1)", color: "var(--foreground)" }}
    >
      {/* ── Nav ──────────────────────────────────────────────── */}
      <nav className="flex items-center gap-4 px-8 py-5 border-b border-white/5">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-sm transition-colors hover:text-white"
          style={{ color: "oklch(0.55 0.02 280)" }}
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Link>
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: "var(--brand)" }}
          >
            <Code2 className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold text-white tracking-tight">RepoTutor</span>
        </div>
      </nav>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="flex-1 flex items-start justify-center px-4 py-14">
        <form
          id="upload-form"
          onSubmit={handleSubmit}
          className="w-full max-w-2xl space-y-8 animate-fade-up"
        >
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight mb-2">
              Analyze your repository
            </h1>
            <p style={{ color: "oklch(0.55 0.02 280)" }} className="text-sm">
              Upload a ZIP of your codebase and tell us a bit about it.
            </p>
          </div>

          {/* ── Step 1: File drop ─────────────────────────────── */}
          <section>
            <h2 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
              >
                1
              </span>
              Upload your ZIP file
            </h2>

            {!file ? (
              <div
                {...getRootProps()}
                id="dropzone"
                className={`
                  rounded-2xl border-2 border-dashed px-8 py-12 text-center cursor-pointer
                  transition-all duration-200
                  ${isDragActive ? "border-[var(--brand)] bg-[var(--brand-dim)]" : "border-white/10 hover:border-white/20 hover:bg-white/[0.02]"}
                `}
              >
                <input {...getInputProps()} id="zip-input" />
                <Upload
                  className="mx-auto mb-4 w-10 h-10"
                  style={{ color: isDragActive ? "var(--brand)" : "oklch(0.4 0.01 280)" }}
                />
                <p className="text-white/70 text-sm mb-1">
                  {isDragActive ? "Release to upload" : "Drag & drop your repository ZIP here"}
                </p>
                <p className="text-xs" style={{ color: "oklch(0.4 0.01 280)" }}>
                  or{" "}
                  <span className="underline underline-offset-2" style={{ color: "var(--brand)" }}>
                    click to browse
                  </span>
                  {" "}· .zip only
                </p>
              </div>
            ) : (
              <div
                className="rounded-2xl border border-white/10 px-6 py-4 flex items-center gap-4"
                style={{ background: "var(--surface-2)" }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: "var(--brand-dim)" }}
                >
                  <FileArchive className="w-5 h-5" style={{ color: "var(--brand)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{file.name}</p>
                  <p className="text-xs mt-0.5" style={{ color: "oklch(0.5 0.02 280)" }}>
                    {formatSize(file.size)}
                  </p>
                </div>
                <button
                  id="remove-file-btn"
                  type="button"
                  onClick={() => setFile(null)}
                  className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                  style={{ color: "oklch(0.5 0.02 280)" }}
                >
                  <X className="w-4 h-4" />
                </button>
                <CheckCircle2 className="w-5 h-5 shrink-0" style={{ color: "oklch(0.65 0.18 145)" }} />
              </div>
            )}
          </section>

          {/* ── Step 2: Product description ───────────────────── */}
          <section className="animate-fade-up delay-100">
            <h2 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
              >
                2
              </span>
              Describe your product{" "}
              <span className="font-normal text-white/30">(optional)</span>
            </h2>
            <Textarea
              id="product-description"
              placeholder="e.g. A SaaS CRM that helps sales teams track leads and automate follow-ups."
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              rows={3}
              className="resize-none border-white/10 bg-white/[0.03] text-white/80 placeholder:text-white/20 focus-visible:ring-[var(--brand)] focus-visible:border-[var(--brand)]"
            />
          </section>

          {/* ── Step 3: Important features ────────────────────── */}
          <section className="animate-fade-up delay-200">
            <h2 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
              >
                3
              </span>
              Features to explain{" "}
              <span className="font-normal text-white/30">(optional)</span>
            </h2>
            <Textarea
              id="important-features"
              placeholder={`e.g. "Explain how a new lead is created" or "Walk me through the billing flow"`}
              value={importantFeatures}
              onChange={(e) => setImportantFeatures(e.target.value)}
              rows={3}
              className="resize-none border-white/10 bg-white/[0.03] text-white/80 placeholder:text-white/20 focus-visible:ring-[var(--brand)] focus-visible:border-[var(--brand)]"
            />
          </section>

          {/* ── Step 4: Audience level ───────────────────────── */}
          <section className="animate-fade-up delay-300">
            <h2 className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-2">
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                style={{ background: "var(--brand-dim)", color: "var(--brand)" }}
              >
                4
              </span>
              Who is this explanation for?
              <div className="relative group ml-1 inline-flex items-center">
                <span className="w-4 h-4 rounded-full border border-white/20 text-white/40 flex items-center justify-center text-[10px] cursor-help font-mono hover:border-white/40 hover:text-white transition-colors">
                  ?
                </span>
                <div className="absolute left-1/2 bottom-full mb-2 -translate-x-1/2 hidden group-hover:block w-72 p-3 bg-slate-900 border border-white/10 rounded-xl shadow-2xl text-xs text-white/80 z-20 transition-all duration-200">
                  <p className="font-semibold text-white mb-1">Audience Levels:</p>
                  <ul className="space-y-1.5 list-disc pl-3.5">
                    <li><strong>Beginner</strong>: Pure conceptual tour. Avoids files & syntax entirely. Uses analogies.</li>
                    <li><strong>Product</strong>: Maps business models & logic flow. Skips low-level helper libraries.</li>
                    <li><strong>Developer</strong>: Direct codebase details, routing patterns, design trade-offs, and file pointers.</li>
                  </ul>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-t-slate-900" />
                </div>
              </div>
            </h2>
            <RadioGroup
              id="technical-level"
              value={technicalLevel}
              onValueChange={(v) => setTechnicalLevel(v as TechnicalLevel)}
              className="space-y-3"
            >
              {levels.map(({ value, label, description }) => (
                <label
                  key={value}
                  htmlFor={`level-${value}`}
                  className={`
                    flex items-start gap-4 rounded-xl border px-5 py-4 cursor-pointer
                    transition-all duration-150
                    ${technicalLevel === value
                      ? "border-[var(--brand)] bg-[var(--brand-dim)]"
                      : "border-white/8 bg-white/[0.02] hover:border-white/15"}
                  `}
                >
                  <RadioGroupItem
                    value={value}
                    id={`level-${value}`}
                    className="mt-0.5 border-white/20 text-[var(--brand)]"
                  />
                  <div>
                    <p className={`text-sm font-semibold ${technicalLevel === value ? "text-white" : "text-white/70"}`}>
                      {label}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "oklch(0.5 0.02 280)" }}>
                      {description}
                    </p>
                  </div>
                </label>
              ))}
            </RadioGroup>
          </section>

          {/* ── Error ─────────────────────────────────────────── */}
          {error && (
            <div
              className="flex items-start gap-3 rounded-xl px-4 py-3 text-sm border"
              style={{
                background: "oklch(0.577 0.245 27 / 10%)",
                borderColor: "oklch(0.577 0.245 27 / 30%)",
                color: "oklch(0.75 0.15 27)",
              }}
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              {error}
            </div>
          )}

          {/* ── Upload progress ───────────────────────────────── */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs" style={{ color: "oklch(0.55 0.02 280)" }}>
                <span>Uploading & analyzing…</span>
                <span>{progress}%</span>
              </div>
              <Progress
                id="upload-progress"
                value={progress}
                className="h-1.5"
                style={
                  {
                    background: "var(--surface-3)",
                    "--tw-ring-color": "var(--brand)",
                  } as React.CSSProperties
                }
              />
            </div>
          )}

          {/* ── Submit ────────────────────────────────────────── */}
          <Button
            id="submit-btn"
            type="submit"
            disabled={uploading || !file}
            size="lg"
            className="w-full h-12 rounded-xl font-semibold text-base text-white disabled:opacity-40"
            style={{ background: uploading || !file ? undefined : "var(--brand)" }}
          >
            {uploading ? (
              <>
                <Loader2 className="mr-2 w-4 h-4 animate-spin" />
                Analyzing repository…
              </>
            ) : (
              <>
                Generate Explanation
                <Upload className="ml-2 w-4 h-4" />
              </>
            )}
          </Button>
        </form>
      </main>
    </div>
  );
}
