"use client";

import { useCallback, useEffect, useState } from "react";

/** localStorage keys */
export const TABLE_THUMB_STORAGE = {
  listings: "watchfinder-listings-thumb-size",
  watchDatabase: "watchfinder-watch-db-thumb-size",
} as const;

const LEGACY_WATCH_DB_KEY = "watchfinder-watch-db-thumb";

export type TableThumbSizeId = "xs" | "sm" | "md" | "lg" | "xl" | "xxl";

export const TABLE_THUMB_OPTIONS: {
  id: TableThumbSizeId;
  label: string;
  sizeClass: string;
}[] = [
  { id: "xs", label: "XS · 32px", sizeClass: "h-8 w-8" },
  { id: "sm", label: "S · 40px", sizeClass: "h-10 w-10" },
  { id: "md", label: "M · 64px", sizeClass: "h-16 w-16" },
  { id: "lg", label: "L · 96px", sizeClass: "h-24 w-24" },
  { id: "xl", label: "XL · 144px", sizeClass: "h-36 w-36" },
  { id: "xxl", label: "2XL · 224px", sizeClass: "h-56 w-56" },
];

const VALID_IDS = new Set(TABLE_THUMB_OPTIONS.map((o) => o.id));

export function getThumbClassById(id: string | null | undefined): string {
  if (id && VALID_IDS.has(id as TableThumbSizeId)) {
    return TABLE_THUMB_OPTIONS.find((o) => o.id === id)!.sizeClass;
  }
  return "h-10 w-10";
}

function parseStoredThumbSize(raw: string | null): TableThumbSizeId {
  if (raw && VALID_IDS.has(raw as TableThumbSizeId)) {
    return raw as TableThumbSizeId;
  }
  return "sm";
}

/**
 * Persisted row thumbnail size for listings or watch database tables.
 * Migrates legacy watch-db `sm` / `lg` boolean key once.
 */
export function usePersistedTableThumbSize(storageKey: string) {
  const [sizeId, setSizeIdState] = useState<TableThumbSizeId>("sm");

  useEffect(() => {
    try {
      let raw = localStorage.getItem(storageKey);
      if (!raw && storageKey === TABLE_THUMB_STORAGE.watchDatabase) {
        const legacy = localStorage.getItem(LEGACY_WATCH_DB_KEY);
        if (legacy === "lg") {
          raw = "md";
          localStorage.setItem(storageKey, raw);
        } else if (legacy === "sm") {
          raw = "sm";
          localStorage.setItem(storageKey, raw);
        }
      }
      setSizeIdState(parseStoredThumbSize(raw));
    } catch {
      setSizeIdState("sm");
    }
  }, [storageKey]);

  const setSizeId = useCallback(
    (id: TableThumbSizeId) => {
      setSizeIdState(id);
      try {
        localStorage.setItem(storageKey, id);
      } catch {
        /* ignore */
      }
    },
    [storageKey],
  );

  const sizeClass = getThumbClassById(sizeId);
  return { sizeId, setSizeId, sizeClass };
}
