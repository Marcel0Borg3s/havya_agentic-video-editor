/** Mirrors src/models/schemas.py exactly. */

export interface CreativeBrief {
  product: string;
  audience: string;
  tone: string;
  duration_seconds: number;
  style_ref: string | null;
}

export interface MediaAsset {
  path: string;
  role: "opening" | "closing" | "music" | "logo" | "other";
}

export interface EditingProfile {
  name: string;
  opening: MediaAsset | null;
  closing: MediaAsset | null;
  editing: {
    remove_silence: boolean;
    silence_threshold: number;
    remove_hesitations: boolean;
    remove_repetitions: boolean;
    detect_bad_takes: boolean;
    detect_scene_changes: boolean;
    transition_type: "cut" | "fade" | "dissolve";
    transition_duration: number;
  };
  captions: {
    enabled: boolean;
    style: string;
    language: string | null;
    position: "top" | "center" | "bottom";
  };
  overlays: Array<{
    role: "title" | "subtitle" | "subscribe" | "credits" | "custom";
    text: string;
    start: number;
    duration: number;
    position: "top" | "center" | "bottom-third" | "bottom";
    style: string;
  }>;
  shorts: {
    enabled: boolean;
    count: number;
    duration_seconds: number;
    aspect_ratio: "9:16";
    captions_enabled: boolean;
    cta_enabled: boolean;
  };
  ai: {
    enabled: boolean;
    provider: string;
    model: string | null;
    api_key_env: string | null;
    base_url: string | null;
  };
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface Shot {
  source_file: string;
  start_time: number;
  end_time: number;
  description: string;
  energy_level: number;
  relevance_score: number;
  transcript: string;
  words: WordTimestamp[];
  roll_type: string;
}

export interface FootageIndex {
  source_dir: string;
  shots: Shot[];
  total_duration: number;
  created_at: string;
}

export interface EditPlanEntry {
  shot_id: string;
  start_trim: number;
  end_trim: number;
  position: number;
  text_overlay: string | null;
  transition: string | null;
}

export interface EditPlan {
  brief: CreativeBrief;
  entries: EditPlanEntry[];
  music_path: string | null;
  total_duration: number;
}

export interface ReviewScore {
  adherence: number;
  pacing: number;
  visual_quality: number;
  watchability: number;
  overall: number;
  feedback: string;
}
