"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/stores/projectStore";
import { FolderPicker } from "@/components/FolderPicker";
import * as api from "@/lib/api";
import {
  FolderOpen,
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Film,
  Scissors,
} from "lucide-react";

export default function ProjectPicker() {
  const router = useRouter();
  const { projects, loading, error, fetchProjects, createProject, deleteProject } =
    useProjectStore();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [footageDir, setFootageDir] = useState("");
  const [rawVideo, setRawVideo] = useState<File | null>(null);
  const [openingFile, setOpeningFile] = useState<File | null>(null);
  const [closingFile, setClosingFile] = useState<File | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [showFolderPicker, setShowFolderPicker] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (!showCreate) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !creating) setShowCreate(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [showCreate, creating]);

  // Poll preprocessing projects.
  useEffect(() => {
    const preprocessing = projects.filter((p) => p.status === "preprocessing");
    if (preprocessing.length === 0) return;
    const timer = setInterval(() => {
      preprocessing.forEach((p) => useProjectStore.getState().pollProject(p.id));
    }, 2000);
    return () => clearInterval(timer);
  }, [projects]);

  const handleCreate = useCallback(async () => {
    if (!name.trim() || (!rawVideo && !footageDir.trim())) return;
    setCreating(true);
    setCreateError("");
    try {
      if (rawVideo) {
        await api.uploadProject(name.trim(), rawVideo, openingFile ?? undefined, closingFile ?? undefined);
        await fetchProjects();
      } else {
        await createProject(name.trim(), footageDir.trim());
      }
      setShowCreate(false);
      setName("");
      setFootageDir("");
      setRawVideo(null);
      setOpeningFile(null);
      setClosingFile(null);
    } catch (e) {
      setCreateError((e as Error).message);
    } finally {
      setCreating(false);
    }
  }, [name, footageDir, rawVideo, openingFile, closingFile, createProject]);

  const statusIcon = (status: string) => {
    switch (status) {
      case "preprocessing":
        return <Loader2 className="w-4 h-4 animate-spin text-amber-400" />;
      case "ready":
        return <CheckCircle2 className="w-4 h-4 text-accent" />;
      case "failed":
        return <AlertCircle className="w-4 h-4 text-destructive" />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-3 mb-8">
          <img src="/branding/havya-white.jpeg" alt="Havya" className="w-10 h-10 rounded object-cover" />
          <h1 className="text-3xl font-bold tracking-tight">Havya Studio</h1>
        </div>

        <div className="mb-8 rounded-xl border border-accent/30 bg-accent/5 p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-accent/15 p-3 text-accent"><Sparkles className="w-6 h-6" /></div>
            <div>
              <h2 className="text-xl font-semibold">Transforme seu vídeo em conteúdo pronto</h2>
              <p className="text-sm text-muted mt-2 max-w-xl">Envie um vídeo bruto e, opcionalmente, uma abertura e uma finalização. O Havya analisa o material, monta o vídeo completo, aplica legendas e prepara Shorts para o YouTube.</p>
              <button onClick={() => setShowCreate(true)} className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded bg-accent hover:bg-accent-hover text-black text-sm font-semibold transition-colors"><Plus className="w-4 h-4" />Criar novo vídeo</button>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-6 pt-5 border-t border-border/60 text-xs text-muted">
            <div className="flex items-center gap-2"><Film className="w-4 h-4 text-accent" /> Vídeo completo</div>
            <div className="flex items-center gap-2"><Scissors className="w-4 h-4 text-accent" /> Cortes automáticos</div>
            <div className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-accent" /> Shorts para YouTube</div>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div><h2 className="text-lg font-medium">Seus vídeos</h2><p className="text-xs text-muted mt-1">Projetos prontos para gerar ou revisar.</p></div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-black text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Novo vídeo
          </button>
        </div>

        {loading && projects.length === 0 && (
          <div className="text-center py-12 text-muted">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Carregando vídeos...
          </div>
        )}

        {error && (
          <div className="text-center py-4 text-destructive text-sm">{error}</div>
        )}

        {!loading && projects.length === 0 && !error && (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <FolderOpen className="w-10 h-10 mx-auto mb-3 text-muted" />
            <p className="text-muted">Ainda não há vídeos. Comece enviando seu vídeo bruto.</p>
            <button onClick={() => setShowCreate(true)} className="mt-4 inline-flex items-center gap-2 px-3 py-2 rounded bg-accent hover:bg-accent-hover text-black text-sm font-medium">
              <Plus className="w-4 h-4" /> Criar primeiro vídeo
            </button>
          </div>
        )}

        <div className="space-y-2">
          {projects.map((p) => (
            <div
              key={p.id}
              className={`flex items-center gap-3 p-4 rounded-lg border transition-colors ${
                p.status === "ready"
                  ? "border-border hover:border-border-hover cursor-pointer bg-surface hover:bg-surface-hover"
                  : "border-border bg-surface opacity-80"
              }`}
              onClick={() => p.status === "ready" && router.push(`/editor/${p.id}`)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {statusIcon(p.status)}
                  <span className="font-medium truncate">{p.name}</span>
                </div>
                <p className="text-xs text-muted mt-1 truncate">{p.footage_dir}</p>
              </div>
              <div className="text-right text-xs text-muted shrink-0">
                {p.status === "ready" && <span>{p.shot_count} shots</span>}
                {p.status === "preprocessing" && <span>Preparando...</span>}
                {p.status === "failed" && (
                  <span className="text-destructive">Failed</span>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteProject(p.id);
                }}
                className="p-1 text-muted hover:text-destructive transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {/* Create dialog */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div role="dialog" aria-modal="true" aria-labelledby="create-title" className="bg-surface border border-border rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
              <h3 id="create-title" className="text-lg font-semibold mb-1">Criar novo vídeo</h3>
              <p className="text-xs text-muted mb-5">Envie um vídeo bruto ou selecione uma pasta local. Abertura e finalização são opcionais.</p>

              <label className="block text-sm text-muted mb-1">Nome do vídeo/projeto</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ex.: Vídeo institucional"
                className="w-full px-3 py-2 rounded border border-border bg-background text-foreground mb-4 focus:outline-none focus:border-accent"
              />

              <label className="block mb-4 rounded border border-accent/30 bg-accent/5 p-3 cursor-pointer">
                <span className="text-sm text-foreground">Enviar vídeo bruto</span>
                <span className="block text-xs text-muted mt-1">Obrigatório se não selecionar uma pasta · MP4, MOV, M4V ou MKV</span>
                <input type="file" accept="video/mp4,video/quicktime,video/x-m4v,video/x-matroska" onChange={(e) => setRawVideo(e.target.files?.[0] ?? null)} className="mt-2 w-full text-xs" />
                {rawVideo && <span className="block text-xs text-accent mt-1">{rawVideo.name}</span>}
              </label>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <label className="rounded border border-border p-3 cursor-pointer"><span className="text-xs text-muted">Intro (opcional)</span><input type="file" accept="video/*" onChange={(e) => setOpeningFile(e.target.files?.[0] ?? null)} className="mt-2 w-full text-[10px]" />{openingFile && <span className="block text-[10px] text-accent mt-1 truncate">{openingFile.name}</span>}</label>
                <label className="rounded border border-border p-3 cursor-pointer"><span className="text-xs text-muted">Finalização (opcional)</span><input type="file" accept="video/*" onChange={(e) => setClosingFile(e.target.files?.[0] ?? null)} className="mt-2 w-full text-[10px]" />{closingFile && <span className="block text-[10px] text-accent mt-1 truncate">{closingFile.name}</span>}</label>
              </div>
              <button
                type="button"
                onClick={() => setShowFolderPicker(true)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded border border-border bg-background text-left mb-4 hover:border-border-hover transition-colors"
              >
                <FolderOpen className="w-4 h-4 text-muted shrink-0" />
                {footageDir ? (
                  <span className="font-mono text-sm truncate">{footageDir}</span>
                ) : (
                  <span className="text-muted text-sm">Ou selecionar pasta com vídeos...</span>
                )}
              </button>

              {createError && (
                <p className="text-destructive text-sm mb-3">{createError}</p>
              )}

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 rounded text-sm text-muted hover:text-foreground transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !name.trim() || (!rawVideo && !footageDir.trim())}
                  className="px-4 py-2 rounded bg-accent hover:bg-accent-hover text-black text-sm font-medium disabled:opacity-50 transition-colors"
                >
                  {creating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Criar vídeo"
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {showFolderPicker && (
        <FolderPicker
          onSelect={(path) => {
            setFootageDir(path);
            setShowFolderPicker(false);
          }}
          onCancel={() => setShowFolderPicker(false)}
        />
      )}
    </div>
  );
}
