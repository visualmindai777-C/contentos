-- Schema MVP. Postgres 13+ (Supabase Free / local). Sin enums ni extensiones para facilitar migraciones.

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text NOT NULL UNIQUE,
  name        text NOT NULL DEFAULT '',
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Un proyecto = un nicho (Curiosidades IA, Historia, Tecnología, Finanzas...)
CREATE TABLE projects (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  slug        text NOT NULL,
  name        text NOT NULL,
  niche       text NOT NULL DEFAULT '',
  language    text NOT NULL DEFAULT 'es',
  config      jsonb NOT NULL DEFAULT '{}',   -- tono, voz TTS, subreddits, keywords semilla
  is_active   boolean NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, slug)
);

CREATE TABLE topics (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  topic       text NOT NULL,
  keywords    jsonb NOT NULL DEFAULT '[]',
  source      text NOT NULL,                  -- google_trends | reddit | ...
  summary     text NOT NULL DEFAULT '',       -- resumen corto que da la propia fuente
  score       numeric(6,2) NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, topic)
);

-- contents.status es la única fuente de verdad del flujo
CREATE TABLE contents (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  topic_id         uuid REFERENCES topics(id) ON DELETE SET NULL,
  status           text NOT NULL DEFAULT 'idea'
                   CHECK (status IN ('idea','guion','generado','revisado','aprobado','publicado','rechazado')),
  title            text NOT NULL DEFAULT '',
  hook             text NOT NULL DEFAULT '',
  script           text NOT NULL DEFAULT '',
  caption          text NOT NULL DEFAULT '',
  hashtags         jsonb NOT NULL DEFAULT '[]',
  cta              text NOT NULL DEFAULT '',
  duration_seconds numeric(6,2) NOT NULL DEFAULT 0,
  llm_provider     text NOT NULL DEFAULT '',
  model_name       text NOT NULL DEFAULT '',
  tokens_used      integer NOT NULL DEFAULT 0,
  parent_id        uuid REFERENCES contents(id) ON DELETE SET NULL,  -- parte anterior de la serie
  part             integer NOT NULL DEFAULT 1,                       -- número de parte (mini novelas)
  last_error       text NOT NULL DEFAULT '',  -- fallo del pipeline; mientras no esté vacío, el contenido espera un reintento manual
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX contents_project_status_idx ON contents (project_id, status);
CREATE INDEX contents_created_idx ON contents (created_at DESC);
CREATE INDEX topics_project_created_idx ON topics (project_id, created_at DESC);

-- Artefactos en almacenamiento de objetos (R2 hoy, cualquier S3 mañana)
CREATE TABLE assets (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id       uuid NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
  kind             text NOT NULL
                   CHECK (kind IN ('video','image','audio','subtitles','caption','hashtags','metadata')),
  storage_provider text NOT NULL DEFAULT 'r2',
  storage_key      text NOT NULL,
  file_size        bigint NOT NULL DEFAULT 0,
  mime_type        text NOT NULL DEFAULT '',
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (content_id, storage_key)
);

CREATE INDEX assets_content_idx ON assets (content_id);

-- Publicación manual registrada por el usuario
CREATE TABLE publications (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id   uuid NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
  platform     text NOT NULL CHECK (platform IN ('tiktok','instagram','threads','x')),
  published_at timestamptz NOT NULL DEFAULT now(),
  notes        text NOT NULL DEFAULT '',
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX publications_content_idx ON publications (content_id);

-- Snapshots de métricas (inmutables: solo created_at)
CREATE TABLE metrics (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  publication_id uuid NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
  views          integer NOT NULL DEFAULT 0,
  likes          integer NOT NULL DEFAULT 0,
  comments       integer NOT NULL DEFAULT 0,
  shares         integer NOT NULL DEFAULT 0,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX metrics_publication_idx ON metrics (publication_id, created_at DESC);

CREATE TRIGGER users_updated BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER projects_updated BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER topics_updated BEFORE UPDATE ON topics FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER contents_updated BEFORE UPDATE ON contents FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER assets_updated BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER publications_updated BEFORE UPDATE ON publications FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Supabase expone `public` vía PostgREST con la anon key: RLS sin políticas lo bloquea.
-- El backend conecta con el rol postgres (bypass RLS).
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE contents ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE metrics ENABLE ROW LEVEL SECURITY;

-- Semilla: un usuario y un proyecto activo
INSERT INTO users (email, name) VALUES ('admin@local', 'Admin') ON CONFLICT DO NOTHING;
INSERT INTO projects (user_id, slug, name, niche, language)
SELECT id, 'curiosidades-ia', 'Curiosidades IA', 'curiosidades sobre inteligencia artificial', 'es'
FROM users WHERE email = 'admin@local'
ON CONFLICT DO NOTHING;
