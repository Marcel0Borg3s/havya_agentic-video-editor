"use client";

import { useState, useEffect, useCallback } from "react";
import { useUiStore } from "@/stores/uiStore";
import { useJobStore } from "@/stores/jobStore";
import { useTimelineStore } from "@/stores/timelineStore";
import { useProjectStore } from "@/stores/projectStore";
import * as api from "@/lib/api";
import type { PipelineEntry, StyleEntry } from "@/types/api";
import { X, Loader2, ChevronDown, ChevronRight } from "lucide-react";

interface RunPipelineDialogProps {
  projectId: string;
}

export function RunPipelineDialog({ projectId }: RunPipelineDialogProps) {
  const open = useUiStore((s) => s.runDialogOpen);
  const setOpen = useUiStore((s) => s.setRunDialogOpen);
  const submitJob = useJobStore((s) => s.submitJob);
  const fetchEditPlan = useTimelineStore((s) => s.fetchEditPlan);
  const project = useProjectStore((s) => s.projects.find((p) => p.id === projectId));

  const [pipelines, setPipelines] = useState<PipelineEntry[]>([]);
  const [styles, setStyles] = useState<StyleEntry[]>([]);
  const [pipelinePath, setPipelinePath] = useState("");
  const [profilePath, setProfilePath] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [product, setProduct] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("energetic");
  const [duration, setDuration] = useState(30);
  const [openingPath, setOpeningPath] = useState("");
  const [closingPath, setClosingPath] = useState("");
  const [title, setTitle] = useState("");
  const [channelName, setChannelName] = useState("");
  const [credits, setCredits] = useState("");
  const [captionsEnabled, setCaptionsEnabled] = useState(true);
  const [shortsEnabled, setShortsEnabled] = useState(true);
  const [shortsCount, setShortsCount] = useState(3);
  const [shortsDuration, setShortsDuration] = useState(60);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      api.getPipelines().then((p) => {
        setPipelines(p);
        if (p.length > 0 && !pipelinePath) setPipelinePath(p[0].path);
      }).catch(() => {});
      api.getStyles().then((s) => {
        setStyles(s);
        if (s.length > 0 && !profilePath) {
          setProfilePath(s.find((x) => x.name === "youtube-default")?.path ?? s[0].path);
        }
      }).catch(() => {});
    }
  }, [open, pipelinePath, profilePath]);

  const handleSubmit = useCallback(async () => {
    if (!project?.footage_index_path || !pipelinePath) return;
    setSubmitting(true);
    setError("");
    try {
      const jobId = await submitJob({
        brief: {
          product: product || project.name || "Product",
          audience: audience || "General",
          tone,
          duration_seconds: duration,
          style_ref: null,
        },
        footage_index_path: project.footage_index_path,
        pipeline_path: pipelinePath,
        profile_path: profilePath || null,
        profile: {
          name: profilePath || "studio-profile",
          opening: openingPath ? { path: openingPath, role: "opening" } : null,
          closing: closingPath ? { path: closingPath, role: "closing" } : null,
          editing: {
            remove_silence: true,
            silence_threshold: 0.8,
            remove_hesitations: true,
            remove_repetitions: true,
            detect_bad_takes: true,
            detect_scene_changes: true,
            transition_type: "cut",
            transition_duration: 0.3,
          },
          captions: { enabled: captionsEnabled, style: "default", language: null, position: "bottom" },
          overlays: [
            ...(title ? [{ role: "title" as const, text: title, start: 0, duration: 5, position: "top" as const, style: "default" }] : []),
            ...(channelName ? [{ role: "subscribe" as const, text: `Inscreva-se em ${channelName}`, start: Math.max(0, duration - 8), duration: 6, position: "bottom" as const, style: "default" }] : []),
            ...(credits ? [{ role: "credits" as const, text: credits, start: Math.max(0, duration - 5), duration: 5, position: "center" as const, style: "default" }] : []),
          ],
          shorts: { enabled: shortsEnabled, count: shortsCount, duration_seconds: shortsDuration, aspect_ratio: "9:16", captions_enabled: captionsEnabled, cta_enabled: true },
          ai: { enabled: true, provider: "gemini", model: null, api_key_env: null, base_url: null },
        },
      });

      setOpen(false);
      useUiStore.getState().toggleConsole();

      // Poll for completion and load edit plan.
      const poll = setInterval(async () => {
        try {
          const job = await api.getJob(jobId);
          if (job.status === "completed") {
            clearInterval(poll);
            fetchEditPlan(jobId);
          } else if (job.status === "failed") {
            clearInterval(poll);
          }
        } catch {
          clearInterval(poll);
        }
      }, 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [product, audience, tone, duration, pipelinePath, profilePath, openingPath, closingPath, title, channelName, credits, captionsEnabled, shortsEnabled, shortsCount, shortsDuration, project, submitJob, fetchEditPlan, setOpen]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-sm bg-surface border border-border rounded-lg shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold">Run Pipeline</h2>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-surface-hover text-muted"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-3 text-xs">
          {/* Pipeline selector */}
          {pipelines.length > 1 && (
            <label className="block">
              <span className="text-muted font-medium">Pipeline</span>
              <select
                value={pipelinePath}
                onChange={(e) => setPipelinePath(e.target.value)}
                className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
              >
                {pipelines.map((p) => (
                  <option key={p.path} value={p.path}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {styles.length > 0 && (
            <label className="block">
              <span className="text-muted font-medium">Editing profile</span>
              <select
                value={profilePath}
                onChange={(e) => setProfilePath(e.target.value)}
                className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
              >
                {styles.map((style) => (
                  <option key={style.path} value={style.path}>
                    {style.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* Footage info */}
          <div className="text-[11px] text-muted bg-background/50 rounded p-2.5">
            <span className="font-medium text-foreground">{project?.name ?? "Project"}</span>
            <span className="ml-2 text-muted">
              {project?.shot_count ?? 0} shots
              {pipelines.length === 1 && (
                <span> -- {pipelines[0].name} pipeline</span>
              )}
            </span>
          </div>

          {/* Advanced toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1 text-muted hover:text-foreground transition-colors"
          >
            {showAdvanced ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span className="text-[11px]">Advanced options</span>
          </button>

          {showAdvanced && (
            <div className="space-y-3 pl-1 border-l-2 border-border ml-1">
              <label className="block pl-2">
                <span className="text-muted font-medium">Product</span>
                <input
                  value={product}
                  onChange={(e) => setProduct(e.target.value)}
                  placeholder={project?.name || "Auto-detected from project"}
                  className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
                />
              </label>

              <label className="block pl-2">
                <span className="text-muted font-medium">Audience</span>
                <input
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  placeholder="General"
                  className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
                />
              </label>

              <div className="flex gap-3 pl-2">
                <label className="flex-1 block">
                  <span className="text-muted font-medium">Tone</span>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
                  >
                    <option value="energetic">Energetic</option>
                    <option value="calm">Calm</option>
                    <option value="professional">Professional</option>
                    <option value="playful">Playful</option>
                    <option value="dramatic">Dramatic</option>
                  </select>
                </label>

                <label className="flex-1 block">
                  <span className="text-muted font-medium">Duration (s)</span>
                  <input
                    type="number"
                    min={5}
                    max={300}
                    value={duration}
                    onChange={(e) => setDuration(parseInt(e.target.value) || 30)}
                    className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
                  />
                </label>
              </div>

              <label className="block pl-2"><span className="text-muted font-medium">Opening path (optional)</span><input value={openingPath} onChange={(e) => setOpeningPath(e.target.value)} placeholder="/path/to/opening.mp4" className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label>
              <label className="block pl-2"><span className="text-muted font-medium">Closing path (optional)</span><input value={closingPath} onChange={(e) => setClosingPath(e.target.value)} placeholder="/path/to/closing.mp4" className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label>
              <label className="block pl-2"><span className="text-muted font-medium">Video title (optional)</span><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title overlay" className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label>
              <label className="block pl-2"><span className="text-muted font-medium">Channel name (optional)</span><input value={channelName} onChange={(e) => setChannelName(e.target.value)} placeholder="My channel" className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label>
              <label className="block pl-2"><span className="text-muted font-medium">Final credits (optional)</span><input value={credits} onChange={(e) => setCredits(e.target.value)} placeholder="Credits" className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label>
              <label className="flex items-center gap-2 pl-2"><input type="checkbox" checked={captionsEnabled} onChange={(e) => setCaptionsEnabled(e.target.checked)} /> Automatic captions</label>
              <label className="flex items-center gap-2 pl-2"><input type="checkbox" checked={shortsEnabled} onChange={(e) => setShortsEnabled(e.target.checked)} /> Generate Shorts</label>
              {shortsEnabled && <div className="flex gap-3 pl-2"><label className="flex-1">Shorts count<input type="number" min={1} max={20} value={shortsCount} onChange={(e) => setShortsCount(Number(e.target.value) || 1)} className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label><label className="flex-1">Short duration<input type="number" min={5} max={180} value={shortsDuration} onChange={(e) => setShortsDuration(Number(e.target.value) || 60)} className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground" /></label></div>}
            </div>
          )}

          {error && (
            <p className="text-destructive text-[10px]">{error}</p>
          )}
        </div>

        <div className="flex justify-end gap-2 px-4 py-3 border-t border-border">
          <button
            onClick={() => setOpen(false)}
            className="px-3 py-1.5 rounded border border-border text-xs hover:bg-surface-hover transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !pipelinePath}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-accent hover:bg-accent-hover text-black text-xs font-medium disabled:opacity-50 transition-colors"
          >
            {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
            Run
          </button>
        </div>
      </div>
    </div>
  );
}
