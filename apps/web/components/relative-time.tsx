"use client";

import { useEffect, useState } from "react";

import { formatRelativeTime } from "@/lib/format-time";

/**
 * Renders a timestamp as relative "x ago" text while preserving the exact ISO
 * value as the element title and `dateTime`.
 *
 * The absolute ISO is shown on the initial (server + first client) render and
 * the relative label is swapped in after mount, avoiding hydration mismatches
 * caused by "now" differing between server and client.
 */
export function RelativeTime({
  iso,
  now,
  className,
}: {
  iso: string;
  now?: number;
  className?: string;
}) {
  const [mounted, setMounted] = useState(now !== undefined);

  useEffect(() => {
    setMounted(true);
  }, []);

  const label = mounted ? formatRelativeTime(iso, now) : iso;

  return (
    <time dateTime={iso} title={iso} className={className}>
      {label}
    </time>
  );
}
