export const STATUSES = ["idea", "guion", "generado", "revisado", "aprobado", "publicado", "rechazado"] as const;
export type Status = (typeof STATUSES)[number];

export const PLATFORMS = ["tiktok", "instagram", "threads", "x"] as const;
export type Platform = (typeof PLATFORMS)[number];

export interface Project {
  id: string;
  slug: string;
  name: string;
  niche: string;
  language: string;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface Topic {
  id: string;
  project_id: string;
  topic: string;
  keywords: string[];
  source: string;
  score: number;
  created_at: string;
}

export interface ContentSummary {
  id: string;
  project_id: string;
  topic_id: string | null;
  status: Status;
  title: string;
  llm_provider: string;
  model_name: string;
  tokens_used: number;
  last_error: string;
  duration_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface Content extends ContentSummary {
  hook: string;
  script: string;
  caption: string;
  hashtags: string[];
  cta: string;
}

export interface Asset {
  id: string;
  kind: "video" | "image" | "audio" | "subtitles" | "caption" | "hashtags" | "metadata";
  storage_key: string;
  file_size: number;
  mime_type: string;
  url: string | null;
}

export interface Publication {
  id: string;
  content_id: string;
  platform: Platform;
  published_at: string;
  notes: string;
}

export interface DashboardStats {
  total: number;
  approved: number;
  published: number;
  rejected: number;
  pending: number;
  scripted: number;
  review: number;
  topics: number;
  queued: number;
  failed: number;
}

export interface PipelineStatus {
  active: boolean;
  last: { conclusion: string | null; updated_at: string; url: string } | null;
}

export interface SystemLimits {
  estimated_tokens_used: number;
  estimated_storage_mb: number;
  estimated_content_count: number;
  free_tier_warnings: string[];
  storage_limit_mb: number;
  llm_calls_today: number;
  llm_daily_limit: number;
}

export interface SystemConfig {
  llm_provider: string;
  llm_models: string[];
  image_provider: string;
  tts_provider: string;
  tts_voice: string;
  tts_lang: string;
  openrouter_daily_limit: number;
  r2_limit_mb: number;
  db_limit_mb: number;
  assets_configured: boolean;
}

export interface IdeaVerdict {
  viable: boolean;
  score: number;
  reason: string;
  risks: string[];
  title: string;
  improvement: string;
  content_id: string | null;
}
