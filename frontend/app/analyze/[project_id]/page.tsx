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
    <div className="min-h-screen flex flex-col bg-transparent text-clay-foreground select-none">
      {/* ── Nav ──────────────────────────────────────────────── */}
      <nav className="flex items-center gap-4 px-8 py-5 border-b border-black/5 bg-white/40 backdrop-blur-md sticky top-0 z-50">
        <Link
          href="/upload"
          className="flex items-center gap-1.5 text-sm font-sans font-bold transition-colors text-clay-muted hover:text-clay-primary"
        >
          <ArrowLeft className="w-4 h-4" />
          Cancel
        </Link>
        <div className="flex items-center gap-2.5 border-l border-black/5 pl-4">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-[#A78BFA] to-[#7C3AED] shadow-clay-button">
            <Code2 className="w-4 h-4 text-white" />
          </div>
          <span className="font-heading font-black text-clay-foreground tracking-tight">RepoTutor</span>
        </div>
      </nav>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        <div className="w-full max-w-xl bg-white/70 backdrop-blur-xl rounded-[40px] border border-black/5 shadow-clay-card p-8 md:p-10 space-y-8 animate-fade-up">
          {error ? (
            <div className="w-full space-y-6 text-center animate-fade-up">
              <div className="mx-auto w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center border-2 border-red-500/20 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
                <AlertCircle className="w-7 h-7 text-red-500" />
              </div>
              <div>
                <h1 className="text-2xl font-heading font-black text-clay-foreground mb-2">Generation Failed</h1>
                <p className="text-sm font-sans font-semibold text-clay-muted mb-4">{error}</p>
              </div>
              <Link href="/upload" className="block">
                <Button className="w-full h-14 rounded-[20px]">
                  <RefreshCw className="mr-2 w-4 h-4 animate-spin-reverse" />
                  Try Again
                </Button>
              </Link>
            </div>
          ) : (
            <div className="w-full space-y-8 animate-fade-up">
              {/* Header */}
              <div className="text-center space-y-3">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-heading font-bold bg-[#EFEBF5] text-clay-primary shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
                  {statusData?.status.startsWith("analyzing") ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 text-clay-secondary animate-pulse" />
                  )}
                  <span>Project ID: <code className="font-mono bg-white/50 px-1 py-0.5 rounded text-[10px]">{project_id}</code></span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-heading font-black text-clay-foreground tracking-tight">
                  {statusData?.status.startsWith("analyzing")
                    ? "Analyzing Codebase..."
                    : "Generating Explanation..."}
                </h1>
                <p className="text-sm font-sans font-medium text-clay-muted">
                  {statusData?.stage || "Setting up..."}
                </p>
              </div>

              {/* Progress bar */}
              <div className="space-y-2 pt-2">
                <div className="flex justify-between text-xs font-heading font-bold text-clay-primary">
                  <span>Overall Progress</span>
                  <span>{statusData?.progress || 0}%</span>
                </div>
                <Progress value={statusData?.progress || 0} />
              </div>

              {/* Vertical Step List */}
              <div className="border border-black/5 rounded-[28px] bg-white/50 p-6 space-y-6 shadow-clay-card">
                <h3 className="text-xs font-heading font-black uppercase tracking-wider text-clay-primary">Pipeline Progress</h3>

                <div className="relative pl-6 border-l-2 border-[#EFEBF5] space-y-6">
                  {PIPELINE_STAGES.map((stage) => {
                    const state = getStageStatus(stage.key);
                    const isExplanations = stage.key === "generating_explanations";
                    const subCounter = getSubCounterText();

                    return (
                      <div key={stage.key} className="relative flex items-center justify-between select-none">
                        {/* Step Indicator Bullet */}
                        <span className="absolute -left-[32px] top-0.5 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-[#F4F1FA]">
                          {state === "completed" && (
                            <CheckCircle2 className="h-5 w-5 text-clay-success bg-[#F4F1FA] rounded-full shrink-0" />
                          )}
                          {state === "active" && (
                            <span className="h-3 w-3 rounded-full bg-clay-primary animate-clay-breathe shadow-clay-button shrink-0" />
                          )}
                          {state === "pending" && (
                            <span className="h-2.5 w-2.5 rounded-full bg-clay-muted/30 shadow-clay-pressed shrink-0" />
                          )}
                        </span>

                        {/* Step Label */}
                        <span
                          className={`text-sm transition-all duration-200 ${
                            state === "active"
                              ? "text-clay-foreground font-heading font-black text-sm"
                              : state === "completed"
                              ? "text-clay-muted/80 font-sans font-semibold"
                              : "text-clay-muted/35 font-sans font-medium"
                          }`}
                        >
                          {stage.label}
                          {isExplanations && state === "active" && subCounter && (
                            <span className="ml-2 text-[10px] font-mono text-white font-bold bg-gradient-to-br from-violet-400 to-violet-600 px-2 py-0.5 rounded-full shadow-clay-button">
                              {subCounter}
                            </span>
                          )}
                        </span>

                        {/* State badge */}
                        {state === "active" && (
                          <Loader2 className="w-4 h-4 text-clay-primary animate-spin shrink-0" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
