import { create } from "zustand";
import type { Project } from "@/types/api";
import * as api from "@/lib/api";

interface ProjectState {
  projects: Project[];
  loading: boolean;
  error: string;
  fetchProjects: () => Promise<void>;
  createProject: (name: string, footageDir: string) => Promise<string>;
  addUploadingProject: (project: { id: string; name: string; status: string }) => void;
  deleteProject: (id: string) => Promise<void>;
  pollProject: (id: string) => Promise<Project>;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  loading: false,
  error: "",

  fetchProjects: async () => {
    set({ loading: true, error: "" });
    try {
      const projects = await api.getProjects();
      set({ projects, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  createProject: async (name, footageDir) => {
    const res = await api.createProject(name, footageDir);
    await get().fetchProjects();
    return res.id;
  },

  addUploadingProject: (project) => {
    const now = new Date().toISOString();
    set({
      projects: [
        ...get().projects.filter((item) => item.id !== project.id),
        {
          id: project.id,
          name: project.name,
          footage_dir: "Upload recebido",
          footage_index_path: "",
          status: project.status as Project["status"],
          shot_count: 0,
          total_duration: 0,
          created_at: now,
          error: null,
        },
      ],
    });
  },

  deleteProject: async (id) => {
    await api.deleteProject(id);
    set({ projects: get().projects.filter((p) => p.id !== id) });
  },

  pollProject: async (id) => {
    let project: Project;
    try {
      project = await api.getProject(id);
    } catch (error) {
      // A backend restart can clear the in-memory project while the UI is
      // polling. Keep the page usable instead of creating an unhandled
      // promise rejection and a stuck loading state.
      if (String(error).includes("Project not found") || String(error).includes("HTTP 404")) {
        set({ projects: get().projects.filter((p) => p.id !== id) });
        return {
          id,
          name: "",
          footage_dir: "",
          footage_index_path: "",
          status: "failed",
          shot_count: 0,
          total_duration: 0,
          created_at: new Date().toISOString(),
          error: "O projeto não está mais disponível. Crie-o novamente.",
        };
      }
      throw error;
    }
    const existing = get().projects;
    const found = existing.some((p) => p.id === id);
    set({
      projects: found
        ? existing.map((p) => (p.id === id ? project : p))
        : [...existing, project],
    });
    return project;
  },
}));
