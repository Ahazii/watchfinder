"use client";

import type { TableThumbSizeId } from "@/lib/table-thumb-sizes";
import { TABLE_THUMB_OPTIONS } from "@/lib/table-thumb-sizes";

export function TableThumbSizeSelect({
  value,
  onChange,
  id,
  compact,
}: {
  value: TableThumbSizeId;
  onChange: (v: TableThumbSizeId) => void;
  id?: string;
  /** Narrower control for table headers */
  compact?: boolean;
}) {
  return (
    <label
      htmlFor={id}
      className={`inline-flex items-center gap-1.5 ${compact ? "text-xs" : "text-sm"}`}
    >
      <span className="whitespace-nowrap text-muted-foreground">Photo size</span>
      <select
        id={id}
        className={`rounded-md border border-border bg-background text-foreground ${
          compact ? "h-7 max-w-[9.5rem] px-1.5 py-0 text-xs" : "h-9 max-w-xs px-2 text-sm"
        }`}
        value={value}
        onChange={(e) => onChange(e.target.value as TableThumbSizeId)}
      >
        {TABLE_THUMB_OPTIONS.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
