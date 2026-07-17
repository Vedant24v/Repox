"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Code2, 
  Download, 
  ArrowLeft, 
  Loader2, 
  Info,
  Layers,
  Sparkles,
  PlayCircle,
  FileText,
  AlertTriangle,
  FolderOpen
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ResultsPayload {
  project_id: string;
  sections: Record<string, string>;
  diagrams: Record<string, string>;
  tech_summary: Record<string, unknown>;
  validation_report: Record<string, unknown>;
  readme: string;
}

interface SidebarItem {
  key: string;
  title: string;
  emoji: string;
  icon: React.ComponentType<{ className?: string }>;
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  { key: "01_start_here", title: "Start Here", emoji: "🚀", icon: Sparkles },
  { key: "02_product_overview", title: "Product Overview", emoji: "📋", icon: FileText },
  { key: "03_tech_stack", title: "Technology Stack", emoji: "🔧", icon: Code2 },
  { key: "04_architecture", title: "Architecture", emoji: "🏗️", icon: Layers },
  { key: "05_component_guide", title: "Important Components", emoji: "🧩", icon: Info },
  { key: "06_main_user_flow", title: "Main User Flow", emoji: "🔄", icon: PlayCircle },
  { key: "07_repo_guide", title: "Repository Guide", emoji: "🗂️", icon: FolderOpen },
  { key: "08_how_to_run", title: "How to Run", emoji: "▶️", icon: PlayCircle },
  { key: "09_unknowns_and_risks", title: "Unknowns and Risks", emoji: "⚠️", icon: AlertTriangle },
  { key: "diagrams", title: "Visual Diagrams", emoji: "📊", icon: Layers }
];

// Mermaid rendering helper component
const MermaidDiagram = ({ mmd, id }: { mmd: string; id: string }) => {
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "default",
          securityLevel: "loose",
          themeVariables: {
            background: "#ffffff",
            primaryColor: "#7c3aed",
            primaryTextColor: "#332f3a",
            primaryBorderColor: "#7c3aed",
            lineColor: "#7c3aed",
            secondaryColor: "#db2777",
            tertiaryColor: "#0ea5e9"
          }
        });
        const { svg: renderedSvg } = await mermaid.render(`mermaid-svg-${id}`, mmd);
        if (isMounted) {
          setSvg(renderedSvg);
        }
      } catch (err: unknown) {
        console.error("Mermaid rendering failed:", err);
        if (isMounted) {
          setError("Could not render this visualization dynamically.");
        }
      }
    };

    renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [mmd, id]);

  if (error) {
    return (
      <div className="bg-red-500/5 border-2 border-red-500/25 rounded-2xl p-6 text-xs text-red-600 font-mono shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
        <p className="font-heading font-bold mb-2">{error}</p>
        <pre className="p-3 bg-[#EFEBF5] rounded-xl overflow-x-auto text-[10px] shadow-clay-pressed">
          {mmd}
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="h-64 flex flex-col items-center justify-center bg-[#EFEBF5] border border-black/5 rounded-2xl shadow-clay-pressed">
        <Loader2 className="w-8 h-8 animate-spin text-clay-primary mb-2" />
        <span className="text-xs font-sans font-semibold text-clay-muted">Generating diagram...</span>
      </div>
    );
  }

  return (
    <div 
      className="p-6 bg-white border border-black/5 rounded-[32px] overflow-auto flex justify-center items-center select-none shadow-clay-card hover:shadow-clay-card-hover transition-all duration-300"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const project_id = params.project_id as string;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ResultsPayload | null>(null);
  const [activeKey, setActiveKey] = useState<string>("01_start_here");

  useEffect(() => {
    if (!project_id) return;

    const fetchResults = async () => {
      try {
        const res = await fetch(`${API_URL}/api/projects/${project_id}/results`);
        if (!res.ok) {
          throw new Error("Results not ready or not found.");
        }
        const payload: ResultsPayload = await res.json();
        setData(payload);
      } catch (err: unknown) {
        console.error("Error fetching project results:", err);
        router.push(`/analyze/${project_id}`);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [project_id, router]);

  // Recursively process text nodes in markdown to highlight badges
  const renderTextWithBadges = (text: string): React.ReactNode => {
    const parts = text.split(/(Confirmed|Inferred|Unclear|Missing)/g);
    return parts.map((part, index) => {
      if (part === "Confirmed") {
        return (
          <span 
            key={index} 
            className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-heading font-black bg-green-500/10 text-green-600 border border-green-500/20 font-sans ml-1 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]"
          >
            Confirmed
          </span>
        );
      }
      if (part === "Inferred") {
        return (
          <span 
            key={index} 
            className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-heading font-black bg-blue-500/10 text-blue-600 border border-blue-500/20 font-sans ml-1 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]"
          >
            Inferred
          </span>
        );
      }
      if (part === "Unclear") {
        return (
          <span 
            key={index} 
            className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-heading font-black bg-yellow-500/10 text-yellow-600 border border-yellow-500/20 font-sans ml-1 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]"
          >
            Unclear
          </span>
        );
      }
      if (part === "Missing") {
        return (
          <span 
            key={index} 
            className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-heading font-black bg-red-500/10 text-red-600 border border-red-500/20 font-sans ml-1 shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]"
          >
            Missing
          </span>
        );
      }
      return part;
    });
  };

  const processNode = (node: React.ReactNode): React.ReactNode => {
    if (typeof node === "string") {
      return renderTextWithBadges(node);
    }
    if (React.isValidElement(node) && node.props && (node.props as { children?: React.ReactNode }).children) {
      return React.cloneElement(
        node, 
        {}, 
        React.Children.map((node.props as { children?: React.ReactNode }).children, processNode)
      );
    }
    return node;
  };

  // Custom react-markdown component styling
  const markdownComponents = {
    h1({ children }: { children?: React.ReactNode }) {
      return <h1 className="text-3xl font-heading font-black text-clay-foreground tracking-tight mb-6 mt-2">{children}</h1>;
    },
    h2({ children }: { children?: React.ReactNode }) {
      return <h2 className="text-xl sm:text-2xl font-heading font-bold text-clay-foreground tracking-tight border-b border-black/5 pb-2 mb-4 mt-8">{children}</h2>;
    },
    h3({ children }: { children?: React.ReactNode }) {
      return <h3 className="text-lg font-heading font-bold text-clay-foreground mb-3 mt-6">{children}</h3>;
    },
    p({ children }: { children?: React.ReactNode }) {
      return <p className="text-base text-clay-foreground/90 font-sans leading-relaxed mb-4">{React.Children.map(children, processNode)}</p>;
    },
    li({ children }: { children?: React.ReactNode }) {
      return <li className="text-sm text-clay-foreground/90 font-sans leading-relaxed mb-2 list-disc ml-5">{React.Children.map(children, processNode)}</li>;
    },
    strong({ children }: { children?: React.ReactNode }) {
      return <strong className="font-bold text-clay-foreground">{children}</strong>;
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    code({ children, ...props }: { children?: React.ReactNode; [key: string]: any }) {
      return (
        <code className="bg-clay-primary/10 px-2 py-0.5 rounded-lg text-sm font-mono text-clay-primary shadow-[inset_0.5px_0.5px_1px_rgba(124,58,237,0.15)]" {...props}>
          {children}
        </code>
      );
    },
    blockquote({ children }: { children?: React.ReactNode }) {
      return (
        <blockquote className="border-l-4 border-clay-primary bg-clay-primary/5 px-5 py-4 my-6 rounded-r-2xl text-clay-foreground/80 font-sans italic text-sm shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]">
          {children}
        </blockquote>
      );
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-transparent text-clay-foreground">
      {/* ── Top Header ─────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-black/5 bg-white/40 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-6">
          <Link
            href="/upload"
            className="flex items-center gap-1.5 text-xs font-sans font-bold text-clay-muted transition-colors hover:text-clay-primary"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            New Upload
          </Link>
          <div className="flex items-center gap-2.5 border-l border-black/5 pl-6">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-gradient-to-br from-[#A78BFA] to-[#7C3AED] shadow-clay-button">
              <Code2 className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-heading font-black text-clay-foreground tracking-tight">Repox Results</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={`${API_URL}/api/projects/${project_id}/download`}
            download
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-[#A78BFA] to-[#7C3AED] px-4 py-2 text-xs font-heading font-black text-white hover:shadow-clay-button-hover hover:-translate-y-0.5 active:scale-95 shadow-clay-button transition-all duration-200"
          >
            <Download className="w-3.5 h-3.5 text-white" />
            Download Full Package (.zip)
          </a>
        </div>
      </header>

      {/* ── Body Container ────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Nav Sidebar */}
        <aside className="w-80 border-r border-black/5 bg-white/20 p-6 space-y-4 overflow-y-auto hidden md:block shrink-0">
          <div className="space-y-1">
            <h3 className="px-3 text-[10px] font-heading font-black uppercase tracking-wider text-clay-muted/40 mb-3">TUTORIAL SECTIONS</h3>
            {SIDEBAR_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeKey === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => setActiveKey(item.key)}
                  className={`
                    w-full flex items-center gap-3 rounded-xl px-4.5 py-3.5 text-sm text-left transition-all duration-200 group border-l-4
                    ${isActive
                      ? "bg-clay-primary/10 text-clay-primary border-clay-primary font-heading font-bold shadow-[inset_1px_1px_2px_rgba(255,255,255,0.6)]"
                      : "text-clay-muted/75 hover:text-clay-primary hover:bg-clay-primary/5 border-transparent"
                    }
                  `}
                >
                  <Icon className={`w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110 ${isActive ? "text-clay-primary" : "text-clay-muted/40"}`} />
                  <span className="truncate">{item.title}</span>
                </button>
              );
            })}
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto px-8 md:px-12 py-10">
          {loading ? (
            // Loading skeleton
            <div className="max-w-4xl space-y-8 animate-pulse bg-white/70 rounded-[36px] shadow-clay-card p-10">
              <div className="h-8 bg-[#EFEBF5] w-1/3 rounded-xl shadow-clay-pressed" />
              <div className="h-4 bg-[#EFEBF5] w-1/4 rounded-xl mb-12 shadow-clay-pressed" />
              <div className="space-y-3">
                <div className="h-4 bg-[#EFEBF5] w-full rounded-lg shadow-clay-pressed" />
                <div className="h-4 bg-[#EFEBF5] w-full rounded-lg shadow-clay-pressed" />
                <div className="h-4 bg-[#EFEBF5] w-5/6 rounded-lg shadow-clay-pressed" />
              </div>
              <div className="h-40 bg-[#EFEBF5] w-full rounded-[24px] mt-12 shadow-clay-pressed" />
            </div>
          ) : (
            <div className="max-w-4xl bg-white/80 border border-black/5 rounded-[36px] shadow-clay-card p-8 md:p-12 hover:shadow-clay-card-hover transition-all duration-300">
              {activeKey === "diagrams" ? (
                // Custom visual diagrams view
                <div className="space-y-10">
                  <div>
                    <h1 className="text-3xl font-heading font-black text-clay-foreground tracking-tight mb-2">Visual Diagrams</h1>
                    <p className="text-sm font-sans font-medium text-clay-muted">Deterministic representations of system flows and directories.</p>
                  </div>
                  
                  <div className="space-y-8">
                    {data?.diagrams && Object.keys(data.diagrams).length > 0 ? (
                      Object.entries(data.diagrams).map(([filename, content]) => {
                        const title = filename.replace(".mmd", "").replace(/_/g, " ");
                        const formattedTitle = title.charAt(0).toUpperCase() + title.slice(1);
                        
                        let caption = "Visual map generated from static repo analysis.";
                        if (filename.includes("system_architecture")) {
                          caption = "Core tiers mapping Frontend, Backend runtime, databases, and AI components.";
                        } else if (filename.includes("main_user_flow")) {
                          caption = "Sequence trace mapping requests and flow between structural modules.";
                        } else if (filename.includes("repository_map")) {
                          caption = "Flow chart of major directories and files across the repository structure.";
                        } else if (filename.includes("database_erd")) {
                          caption = "Relationship map showing identified data entities and relationships.";
                        }

                        return (
                          <div key={filename} className="border border-black/5 rounded-[28px] bg-white/50 p-6 space-y-4 shadow-clay-card hover:-translate-y-1 hover:shadow-clay-card-hover transition-all duration-300">
                            <div>
                              <h3 className="text-lg font-heading font-bold text-clay-foreground capitalize">{formattedTitle}</h3>
                              <p className="text-xs font-sans font-medium text-clay-muted mt-1">{caption}</p>
                            </div>
                            <MermaidDiagram mmd={content} id={filename.replace(/\./g, "-")} />
                          </div>
                        );
                      })
                    ) : (
                      <div className="p-8 text-center font-sans font-medium text-clay-muted border border-black/5 bg-[#EFEBF5] rounded-2xl shadow-clay-pressed">
                        No diagram assets were generated for this project.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                // Markdown content view
                <article className="prose prose-slate max-w-none">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    components={markdownComponents as any}
                  >
                    {data?.sections[activeKey] || "# Section details not found"}
                  </ReactMarkdown>
                </article>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
