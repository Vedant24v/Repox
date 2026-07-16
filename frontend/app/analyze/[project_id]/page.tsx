"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { 
  Code2, 
  Clock, 
  CheckCircle2, 
  Loader2, 
  AlertCircle, 
  ArrowLeft, 
  RefreshCw 
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StatusResponse {
  project_id: string;
  status: string;
  stage: string;
  progress: number;
  is_complete: boolean;
  is_error: boolean;
  error_message?: string;
}

const PIPELINE_STAGES = [
  { key: "reading_files", label: "Reading repository files" },
  { key: "detecting_tech", label: "Confirming tech stack" },
  { key: "finding_components", label: "Identifying components" },
  { key: "mapping_relationships", label: "Mapping relationships" },
  { key: "identifying_flow", label: "Summarising files with LLM" },
  { key: "generating_explanations", label: "Generating tutorial explanations" },
  { key: "generating_diagrams", label: "Generating visualizations" },
  { key: "validating", label: "Running validation checks" },
  { key: "packaging", label: "Packaging output archive" }
];

export default function AnalyzePage() {
  const router = useRouter();
  const params = useParams();
  const project_id = params.project_id as string;

  const [statusData, setStatusData] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const triggerCalled = useRef(false);

  useEffect(() => {
    if (!project_id) return;

    let pollInterval: NodeJS.Timeout | undefined = undefined;

    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/projects/${project_id}/status`);
        if (!res.ok) {
          throw new Error("Failed to fetch project status.");
        }
        const data: StatusResponse = await res.json();
        setStatusData(data);

        // If backend analysis is complete but tutorial generation hasn't started yet
        if (data.status === "analyzed" && !triggerCalled.current) {
          triggerCalled.current = true;
          startGeneration();
        }

        // Redirect to results once complete
        if (data.status === "complete" || (data.is_complete && data.status !== "analyzed")) {
          if (pollInterval) clearInterval(pollInterval);
          router.push(`/results/${project_id}`);
        }

        // Handle error
        if (data.is_error || data.status === "error") {
          if (pollInterval) clearInterval(pollInterval);
          setError(data.error_message || "Pipeline failed. Please try again.");
        }
      } catch (err: unknown) {
        console.error("Error polling status:", err);
      }
    };

    const startGeneration = async () => {
      try {
        const res = await fetch(`${API_URL}/api/projects/${project_id}/generate`, {
          method: "POST"
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData?.detail?.message ?? "Failed to trigger tutorial generation.");
        }
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : "Failed to start tutorial generation.";
        setError(errMsg);
        if (pollInterval) clearInterval(pollInterval);
      }
    };

    // Initial check
    pollStatus();

    // Poll every 2s
    pollInterval = setInterval(pollStatus, 2000);

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [project_id, router]);

  // Determine stage active indexes
  const getStageStatus = (stageKey: string) => {
    if (!statusData) return "pending";
    const currentStatus = statusData.status;

    // Mapping currentStatus to active index
    let currentIdx = -1;
    if (currentStatus.startsWith("generating_explanations")) {
      currentIdx = PIPELINE_STAGES.findIndex(s => s.key === "generating_explanations");
    } else {
      currentIdx = PIPELINE_STAGES.findIndex(s => s.key === currentStatus);
    }

    const stageIdx = PIPELINE_STAGES.findIndex(s => s.key === stageKey);

    if (currentStatus === "complete") {
      return "completed";
    }
    
    if (currentIdx === -1) {
      // If we are in initial static analysis stage, all generation steps are pending
      return "pending";
    }

    if (stageIdx < currentIdx) return "completed";
    if (stageIdx === currentIdx) return "active";
    return "pending";
  };

  const getSubCounterText = () => {
    if (!statusData) return null;
    const match = statusData.status.match(/\((\d+\/\d+)\)/);
    return match ? match[1] : null;
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--surface-1)", color: "var(--foreground)" }}
    >
      {/* ── Nav ──────────────────────────────────────────────── */}
      <nav className="flex items-center gap-4 px-8 py-5 border-b border-white/5">
        <Link
          href="/upload"
          className="flex items-center gap-1.5 text-sm transition-colors hover:text-white"
          style={{ color: "oklch(0.55 0.02 280)" }}
        >
          <ArrowLeft className="w-4 h-4" />
          Cancel
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
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-10 max-w-xl mx-auto w-full">
        {error ? (
          <div className="w-full space-y-6 text-center animate-fade-up">
            <div className="mx-auto w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/30">
              <AlertCircle className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white mb-2">Generation Failed</h1>
              <p className="text-sm text-white/60 mb-4">{error}</p>
            </div>
            <Link href="/upload" className="block">
              <Button className="w-full bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white">
                <RefreshCw className="mr-2 w-4 h-4" />
                Try Again
              </Button>
            </Link>
          </div>
        ) : (
          <div className="w-full space-y-8 animate-fade-up">
            {/* Header */}
            <div className="text-center space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs bg-white/5 text-white/80 border border-white/10">
                {statusData?.status.startsWith("analyzing") ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Clock className="w-3 h-3 text-[var(--brand)]" />
                )}
                <span>Project ID: <code className="font-mono">{project_id}</code></span>
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                {statusData?.status.startsWith("analyzing")
                  ? "Analyzing Codebase..."
                  : "Generating Explanation report..."}
              </h1>
              <p className="text-sm text-white/50">
                {statusData?.stage || "Setting up..."}
              </p>
            </div>

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-white/40">
                <span>Overall Progress</span>
                <span>{statusData?.progress || 0}%</span>
              </div>
              <Progress 
                value={statusData?.progress || 0} 
                className="h-2 bg-white/5"
                style={{ "--tw-ring-color": "var(--brand)" } as React.CSSProperties}
              />
            </div>

            {/* Vertical Step List */}
            <div className="border border-white/5 rounded-2xl bg-white/[0.01] p-6 space-y-6">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-white/40">Pipeline Progress</h3>
              
              <div className="relative pl-6 border-l border-white/10 space-y-6">
                {PIPELINE_STAGES.map((stage) => {
                  const state = getStageStatus(stage.key);
                  const isExplanations = stage.key === "generating_explanations";
                  const subCounter = getSubCounterText();

                  return (
                    <div key={stage.key} className="relative flex items-center justify-between">
                      {/* Step Indicator Bullet */}
                      <span className="absolute -left-[31px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-slate-950 border border-white/10">
                        {state === "completed" && (
                          <CheckCircle2 className="h-4.5 w-4.5 text-green-500 bg-slate-950 rounded-full" />
                        )}
                        {state === "active" && (
                          <span className="h-2 w-2 rounded-full bg-[var(--brand)] animate-ping" />
                        )}
                        {state === "pending" && (
                          <span className="h-1.5 w-1.5 rounded-full bg-white/20" />
                        )}
                      </span>

                      {/* Step Label */}
                      <span 
                        className={`text-sm transition-all duration-200 ${
                          state === "active" 
                            ? "text-white font-medium" 
                            : state === "completed" 
                            ? "text-white/60" 
                            : "text-white/30"
                        }`}
                      >
                        {stage.label}
                        {isExplanations && state === "active" && subCounter && (
                          <span className="ml-2 text-xs font-mono text-[var(--brand)] font-semibold bg-[var(--brand-dim)] px-2 py-0.5 rounded-full">
                            {subCounter}
                          </span>
                        )}
                      </span>

                      {/* State badge */}
                      {state === "active" && (
                        <Loader2 className="w-4 h-4 text-[var(--brand)] animate-spin" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
