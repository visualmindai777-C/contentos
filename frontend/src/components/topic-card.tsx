"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { deleteTopic, queueVideoFromTopic } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Virality } from "@/components/virality";
import type { Topic } from "@/lib/types";
import { formatAgo } from "@/lib/utils";

const SOURCES: Record<string, string> = {
  google_trends: "Google Trends", reddit: "Reddit", wikipedia: "Wikipedia", hackernews: "Hacker News", manual: "A mano",
};

export function TopicCard({ topic }: { topic: Topic }) {
  const [pending, start] = useTransition();
  const [created, setCreated] = useState<string>();
  const [error, setError] = useState<string>();
  const [gone, setGone] = useState(false);
  const [open, setOpen] = useState(false);
  if (gone) return null;

  const long = topic.summary.length > 140;
  return (
    <article className="space-y-3 rounded-lg border bg-card p-4">
      <div className="space-y-1">
        <h3 className="font-semibold leading-snug">{topic.topic}</h3>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Virality score={topic.score} />
          <span className="text-xs text-muted-foreground">{SOURCES[topic.source] ?? topic.source} · {formatAgo(topic.created_at)}</span>
          {topic.used && !created && <Badge variant="info">Ya tiene video</Badge>}
        </div>
      </div>

      {topic.summary && (
        <p className="text-sm text-muted-foreground">
          <span className={open ? "" : "line-clamp-3"}>{topic.summary}</span>
          {long && (
            <button type="button" onClick={() => setOpen(!open)} className="ml-1 font-medium text-foreground underline">
              {open ? "ver menos" : "ver más"}
            </button>
          )}
        </p>
      )}

      {created ? (
        <div className="flex items-center justify-between gap-2 rounded-md bg-green-50 p-3 text-sm text-green-900" role="status">
          <span>✓ Video en cola</span>
          <Link href={`/contents/${created}`} className="font-semibold underline">Ver</Link>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button
            className="flex-1"
            variant={topic.used ? "outline" : "default"}
            disabled={pending}
            onClick={() => start(async () => {
              const res = await queueVideoFromTopic(topic.project_id, topic.id, topic.topic);
              setCreated(res.id);
              setError(res.error);
            })}
          >
            {pending ? "Creando…" : topic.used ? "Crear otro video" : "Crear video"}
          </Button>
          <Button
            variant="outline"
            disabled={pending}
            aria-label={`Descartar «${topic.topic}»`}
            onClick={() => start(async () => {
              const err = await deleteTopic(topic.id);
              if (err) setError(err);
              else setGone(true);
            })}
          >
            Descartar
          </Button>
        </div>
      )}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </article>
  );
}
