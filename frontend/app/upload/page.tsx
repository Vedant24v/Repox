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
    <div className="min-h-screen flex flex-col bg-transparent text-clay-foreground select-none">
      {/* ── Nav ──────────────────────────────────────────────── */}
      <nav className="flex items-center gap-4 px-8 py-5 border-b border-black/5 bg-white/40 backdrop-blur-md sticky top-0 z-50">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-sm font-sans font-bold transition-colors text-clay-muted hover:text-clay-primary"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Link>
        <div className="flex items-center gap-2.5 border-l border-black/5 pl-4">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-[#A78BFA] to-[#7C3AED] shadow-clay-button">
            <Code2 className="w-4 h-4 text-white" />
          </div>
          <span className="font-heading font-black text-clay-foreground tracking-tight">Repox</span>
        </div>
      </nav>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="flex-1 flex items-start justify-center px-4 py-14">
        <form
          id="upload-form"
          onSubmit={handleSubmit}
          className="w-full max-w-2xl bg-white/70 backdrop-blur-xl rounded-[40px] border border-black/5 shadow-clay-card p-8 md:p-12 space-y-8 animate-fade-up"
        >
          {/* Header */}
          <div>
            <h1 className="text-3xl sm:text-4xl font-heading font-black text-clay-foreground tracking-tight mb-2">
              Analyze your repository
            </h1>
            <p className="text-sm text-clay-muted font-sans font-medium">
              Upload a ZIP of your codebase and tell us a bit about it.
            </p>
          </div>

          {/* ── Step 1: File drop ─────────────────────────────── */}
          <section className="space-y-3">
            <h2 className="text-base font-heading font-bold text-clay-foreground flex items-center gap-2.5">
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-heading font-black bg-clay-primary/10 text-clay-primary shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
                1
              </span>
              Upload your ZIP file
            </h2>

            {!file ? (
              <div
                {...getRootProps()}
                id="dropzone"
                className={`
                  rounded-[28px] border-4 border-dashed px-8 py-14 text-center cursor-pointer
                  transition-all duration-300 shadow-clay-pressed
                  ${isDragActive ? "border-clay-primary bg-clay-primary/5 scale-[1.02]" : "border-clay-primary/20 bg-[#EFEBF5] hover:border-clay-primary/45 hover:scale-[1.01]"}
                `}
              >
                <input {...getInputProps()} id="zip-input" />
                <Upload
                  className="mx-auto mb-4 w-12 h-12 transition-colors duration-300"
                  style={{ color: isDragActive ? "var(--color-clay-primary)" : "var(--color-clay-muted)" }}
                />
                <p className="text-clay-foreground font-heading font-bold text-base mb-1.5">
                  {isDragActive ? "Release to upload!" : "Drag & drop your repository ZIP here"}
                </p>
                <p className="text-xs text-clay-muted font-sans font-semibold">
                  or{" "}
                  <span className="underline underline-offset-2 text-clay-primary hover:text-clay-primary-hover">
                    click to browse
                  </span>
                  {" "}· .zip only
                </p>
              </div>
            ) : (
              <div className="rounded-[28px] border border-black/5 bg-white/80 px-6 py-5 flex items-center gap-4 shadow-clay-card hover:-translate-y-1 hover:shadow-clay-card-hover transition-all duration-300">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 bg-gradient-to-br from-violet-400 to-violet-600 shadow-clay-button text-white">
                  <FileArchive className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-heading font-bold text-clay-foreground truncate">{file.name}</p>
                  <p className="text-xs font-sans font-semibold text-clay-muted mt-0.5">
                    {formatSize(file.size)}
                  </p>
                </div>
                <button
                  id="remove-file-btn"
                  type="button"
                  onClick={() => setFile(null)}
                  className="p-2 rounded-xl bg-[#EFEBF5] shadow-clay-button hover:-translate-y-0.5 active:scale-90 hover:bg-red-500 hover:text-white transition-all text-clay-muted"
                >
                  <X className="w-4 h-4" />
                </button>
                <CheckCircle2 className="w-6 h-6 shrink-0 text-clay-success" />
              </div>
            )}
          </section>

          {/* ── Step 2: Product description ───────────────────── */}
          <section className="animate-fade-up delay-100 space-y-3">
            <h2 className="text-base font-heading font-bold text-clay-foreground flex items-center gap-2.5">
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-heading font-black bg-clay-primary/10 text-clay-primary shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
                2
              </span>
              Describe your product{" "}
              <span className="font-sans font-medium text-clay-muted/65 text-xs"> (optional)</span>
            </h2>
            <Textarea
              id="product-description"
              placeholder="e.g. A SaaS CRM that helps sales teams track leads and automate follow-ups."
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              rows={3}
            />
          </section>

          {/* ── Step 3: Important features ────────────────────── */}
          <section className="animate-fade-up delay-200 space-y-3">
            <h2 className="text-base font-heading font-bold text-clay-foreground flex items-center gap-2.5">
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-heading font-black bg-clay-primary/10 text-clay-primary shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
                3
              </span>
              Features to explain{" "}
              <span className="font-sans font-medium text-clay-muted/65 text-xs"> (optional)</span>
            </h2>
            <Textarea
              id="important-features"
              placeholder={`e.g. "Explain how a new lead is created" or "Walk me through the billing flow"`}
              value={importantFeatures}
              onChange={(e) => setImportantFeatures(e.target.value)}
              rows={3}
            />
          </section>

          {/* ── Step 4: Audience level ───────────────────────── */}
          <section className="animate-fade-up delay-300 space-y-4">
            <h2 className="text-base font-heading font-bold text-clay-foreground flex items-center gap-2.5">
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-heading font-black bg-clay-primary/10 text-clay-primary shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
                4
              </span>
              Who is this explanation for?
              <div className="relative group ml-1 inline-flex items-center">
                <span className="w-5 h-5 rounded-full border border-clay-muted/30 text-clay-muted flex items-center justify-center text-xs cursor-help font-mono hover:border-clay-primary hover:text-clay-primary transition-colors bg-[#EFEBF5]">
                  ?
                </span>
                <div className="absolute left-1/2 bottom-full mb-3 -translate-x-1/2 hidden group-hover:block w-72 p-4 bg-white border border-black/5 rounded-2xl shadow-clay-card text-xs text-clay-foreground z-20 transition-all duration-200 select-none">
                  <p className="font-heading font-bold text-clay-primary mb-1.5">Audience Levels:</p>
                  <ul className="space-y-1.5 list-disc pl-3.5 font-sans font-medium text-clay-muted">
                    <li><strong>Beginner</strong>: Pure conceptual tour. Avoids syntax. Uses analogies.</li>
                    <li><strong>Product</strong>: Maps business models & logic flow. Skips helper details.</li>
                    <li><strong>Developer</strong>: Direct codebase structure, routing, design details.</li>
                  </ul>
                </div>
              </div>
            </h2>
            <RadioGroup
              id="technical-level"
              value={technicalLevel}
              onValueChange={(v) => setTechnicalLevel(v as TechnicalLevel)}
              className="space-y-3"
            >
              {levels.map(({ value, label, description }) => {
                const isSelected = technicalLevel === value;
                return (
                  <label
                    key={value}
                    htmlFor={`level-${value}`}
                    className={`
                      flex items-start gap-4 rounded-[24px] px-5 py-4 cursor-pointer
                      transition-all duration-300 select-none border-2
                      ${isSelected
                        ? "border-clay-primary bg-white shadow-clay-card -translate-y-0.5"
                        : "border-transparent bg-[#EFEBF5] shadow-clay-pressed hover:scale-[1.005]"}
                    `}
                  >
                    <RadioGroupItem
                      value={value}
                      id={`level-${value}`}
                      className="mt-0.5"
                    />
                    <div>
                      <p className={`text-sm font-heading font-bold ${isSelected ? "text-clay-primary" : "text-clay-foreground"}`}>
                        {label}
                      </p>
                      <p className="text-xs font-sans font-medium text-clay-muted mt-0.5 leading-relaxed">
                        {description}
                      </p>
                    </div>
                  </label>
                );
              })}
            </RadioGroup>
          </section>

          {/* ── Error ─────────────────────────────────────────── */}
          {error && (
            <div
              className="flex items-start gap-3 rounded-2xl px-5 py-4 text-sm border-2 border-red-500/25 bg-red-500/5 text-red-600 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)] font-sans font-bold"
            >
              <AlertCircle className="w-5 h-5 shrink-0" />
              {error}
            </div>
          )}

          {/* ── Upload progress ───────────────────────────────── */}
          {uploading && (
            <div className="space-y-2 pt-2">
              <div className="flex justify-between text-xs font-heading font-bold text-clay-primary">
                <span>Uploading & analyzing…</span>
                <span>{progress}%</span>
              </div>
              <Progress
                id="upload-progress"
                value={progress}
              />
            </div>
          )}

          {/* ── Submit ────────────────────────────────────────── */}
          <Button
            id="submit-btn"
            type="submit"
            disabled={uploading || !file}
            size="lg"
            className="w-full h-16 rounded-[20px] font-heading font-black text-lg text-white"
          >
            {uploading ? (
              <>
                <Loader2 className="mr-2 w-5 h-5 animate-spin" />
                Analyzing repository…
              </>
            ) : (
              <>
                Generate Explanation
                <Upload className="ml-2 w-5 h-5" />
              </>
            )}
          </Button>
        </form>
      </main>
    </div>
  );
}
