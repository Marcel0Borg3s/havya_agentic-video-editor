"use client";

import { useState, useEffect, useCallback } from "react";
import { useUiStore } from "@/stores/uiStore";
import { useJobStore } from "@/stores/jobStore";
import { useTimelineStore } from "@/stores/timelineStore";
import { useProjectStore } from "@/stores/projectStore";
import * as api from "@/lib/api";
import type { PipelineEntry, StyleEntry } from "@/types/api";
import { X, Loader2, ChevronDown, ChevronRight, Film, Type, MessageSquare, Video } from "lucide-react";

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
  const [showAssets, setShowAssets] = useState(false);
  const [showOverlays, setShowOverlays] = useState(true);
  const [product, setProduct] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("energetic");
  const [duration, setDuration] = useState(30);

  // Auto-detect duration from project when dialog opens.
  useEffect(() => {
    if (open && project?.total_duration && project.total_duration > 0) {
      setDuration(Math.round(project.total_duration));
    }
  }, [open, project?.total_duration]);
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
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setLoadingOptions(true);
    setError("");
    const pipelineRequest = api.getPipelines().then((p) => {
      setPipelines(p);
      if (p.length > 0 && !pipelinePath) setPipelinePath(p[0].path);
    }).catch(() => setError("Nao foi possivel carregar os pipelines."));
    const styleRequest = api.getStyles().then((s) => {
      setStyles(s);
      if (s.length > 0 && !profilePath) {
        setProfilePath(s.find((x) => x.name === "youtube-default")?.path ?? s[0].path);
      }
    }).catch(() => setError("Nao foi possivel carregar os perfis."));
    Promise.allSettled([pipelineRequest, styleRequest]).finally(() => setLoadingOptions(false));
  }, [open, pipelinePath, profilePath]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, submitting, setOpen]);

  const handleSubmit = useCallback(async () => {
    if (!project?.footage_index_path || !pipelinePath || project.status !== "ready") return;
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
      <div className="w-full max-w-md bg-surface border border-border rounded-lg shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border sticky top-0 bg-surface">
          <div><h2 className="text-sm font-semibold">Gerar video</h2><p className="text-[10px] text-muted">Configure o video completo e Shorts.</p></div>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-surface-hover text-muted"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4 text-xs">
          <div className="rounded-lg border border-accent/30 bg-accent/5 p-3">
            <p className="font-medium text-foreground">Video bruto</p>
            <p className="text-muted mt-1">{project?.name ?? "Projeto atual"} · {project?.shot_count ?? 0} cenas analisadas</p>
          </div>

          {/* Pipeline & Profile */}
          <div className="space-y-2">
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
                <span className="text-muted font-medium">Perfil de edicao</span>
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
          </div>

          {/* Titulo e Creditos - sempre visivel */}
          <div className="rounded-lg border border-border p-3 space-y-2">
            <div className="flex items-center gap-2 text-muted font-medium">
              <Type className="w-3 h-3" />
              <span>Texto no video</span>
            </div>
            <label className="block">
              <span className="text-muted">Titulo (opcional)</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex: Meu Video Incrivel"
                className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
              />
            </label>
            <label className="block">
              <span className="text-muted">Nome do canal (opcional)</span>
              <input
                value={channelName}
                onChange={(e) => setChannelName(e.target.value)}
                placeholder="Ex: Meu Canal"
                className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
              />
            </label>
            <label className="block">
              <span className="text-muted">Creditos (opcional)</span>
              <input
                value={credits}
                onChange={(e) => setCredits(e.target.value)}
                placeholder="Ex: Producao: Havya Studio"
                className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground focus:outline-none focus:border-accent"
              />
            </label>
          </div>

          {/* Legendas - sempre visivel */}
          <div className="rounded-lg border border-border p-3">
            <label className="flex items-center gap-2">
              <MessageSquare className="w-3 h-3 text-muted" />
              <input
                type="checkbox"
                checked={captionsEnabled}
                onChange={(e) => setCaptionsEnabled(e.target.checked)}
                className="rounded"
              />
              <span className="text-muted font-medium">Legendas automaticas</span>
            </label>
            <p className="text-muted text-[10px] mt-1 ml-5">
              Gera legendas a partir da transcricao do audio
            </p>
          </div>

          {/* Assets (Intro/Finalizacao) - colapsavel */}
          <div className="rounded-lg border border-border">
            <button
              onClick={() => setShowAssets(!showAssets)}
              className="flex items-center gap-2 w-full p-3 text-left text-muted hover:text-foreground transition-colors"
            >
              <Film className="w-3 h-3" />
              <span className="font-medium text-xs">Intro e Finalizacao</span>
              <span className="text-[10px] ml-auto">(opcional)</span>
              {showAssets ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
            {showAssets && (
              <div className="px-3 pb-3 space-y-2 border-t border-border pt-2">
                <label className="block">
                  <span className="text-muted">Caminho do video de abertura</span>
                  <input
                    value={openingPath}
                    onChange={(e) => setOpeningPath(e.target.value)}
                    placeholder="/caminho/para/intro.mp4"
                    className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                  />
                </label>
                <label className="block">
                  <span className="text-muted">Caminho do video de fechamento</span>
                  <input
                    value={closingPath}
                    onChange={(e) => setClosingPath(e.target.value)}
                    placeholder="/caminho/para/final.mp4"
                    className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                  />
                </label>
              </div>
            )}
          </div>

          {/* Shorts - sempre visivel */}
          <div className="rounded-lg border border-border p-3 space-y-2">
            <label className="flex items-center gap-2">
              <Video className="w-3 h-3 text-muted" />
              <input
                type="checkbox"
                checked={shortsEnabled}
                onChange={(e) => setShortsEnabled(e.target.checked)}
                className="rounded"
              />
              <span className="text-muted font-medium">Gerar Shorts</span>
            </label>
            {shortsEnabled && (
              <div className="flex gap-3 ml-5 mt-2">
                <label className="flex-1">
                  <span className="text-muted text-[10px]">Quantidade</span>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={shortsCount}
                    onChange={(e) => setShortsCount(Number(e.target.value) || 1)}
                    className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                  />
                </label>
                <label className="flex-1">
                  <span className="text-muted text-[10px]">Duracao max (s)</span>
                  <input
                    type="number"
                    min={5}
                    max={180}
                    value={shortsDuration}
                    onChange={(e) => setShortsDuration(Number(e.target.value) || 60)}
                    className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                  />
                </label>
              </div>
            )}
          </div>

          {/* Opcoes avancadas - colapsavel */}
          <div className="rounded-lg border border-border">
            <button
              onClick={() => setShowOverlays(!showOverlays)}
              className="flex items-center gap-2 w-full p-3 text-left text-muted hover:text-foreground transition-colors"
            >
              <span className="font-medium text-xs">Configuracao avancada</span>
              {showOverlays ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
            {showOverlays && (
              <div className="px-3 pb-3 space-y-2 border-t border-border pt-2">
                <div className="flex gap-3">
                  <label className="flex-1 block">
                    <span className="text-muted">Product</span>
                    <input
                      value={product}
                      onChange={(e) => setProduct(e.target.value)}
                      placeholder={project?.name || "Auto-detect"}
                      className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                    />
                  </label>
                  <label className="flex-1 block">
                    <span className="text-muted">Audience</span>
                    <input
                      value={audience}
                      onChange={(e) => setAudience(e.target.value)}
                      placeholder="General"
                      className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                    />
                  </label>
                </div>
                <div className="flex gap-3">
                  <label className="flex-1 block">
                    <span className="text-muted">Tom</span>
                    <select
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                    >
                      <option value="energetic">Energetico</option>
                      <option value="calm">Calmo</option>
                      <option value="professional">Profissional</option>
                      <option value="playful">Descontraido</option>
                      <option value="dramatic">Dramatico</option>
                    </select>
                  </label>
                  <label className="flex-1 block">
                    <span className="text-muted">Duracao alvo (s) — auto-detectada: {project?.total_duration ? `${Math.round(project.total_duration)}s` : 'N/A'}</span>
                    <input
                      type="number"
                      min={5}
                      max={300}
                      value={duration}
                      onChange={(e) => setDuration(parseInt(e.target.value) || 30)}
                      className="w-full mt-1 px-2 py-1.5 rounded border border-border bg-background text-foreground"
                    />
                  </label>
                </div>
              </div>
            )}
          </div>

          {error && (
            <p className="text-destructive text-[10px]">{error}</p>
          )}
          {project?.status !== "ready" && (
            <p className="text-amber-400 text-[10px]">Aguarde o processamento do video terminar antes de gerar.</p>
          )}
        </div>

        <div className="flex justify-end gap-2 px-4 py-3 border-t border-border sticky bottom-0 bg-surface">
          <button
            onClick={() => setOpen(false)}
            className="px-3 py-1.5 rounded border border-border text-xs hover:bg-surface-hover transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || loadingOptions || !pipelinePath || project?.status !== "ready"}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-accent hover:bg-accent-hover text-black text-xs font-medium disabled:opacity-50 transition-colors"
          >
            {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
            Gerar video
          </button>
        </div>
      </div>
    </div>
  );
}
