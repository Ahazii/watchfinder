"use client";

import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type SortDir = "asc" | "desc";

type Props = {
  label: string;
  column: string;
  sortBy: string;
  sortDir: SortDir;
  onSort: (column: string) => void;
  className?: string;
};

export function SortableTableHead({
  label,
  column,
  sortBy,
  sortDir,
  onSort,
  className,
}: Props) {
  const active = sortBy === column;
  return (
    <TableHead className={className}>
      <button
        type="button"
        className={cn(
          "-ml-2 inline-flex items-center gap-1 rounded-md px-2 py-1 text-left font-medium text-foreground hover:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
          active && "bg-muted/50",
        )}
        onClick={() => onSort(column)}
      >
        {label}
        {active ? (
          <span className="tabular-nums text-muted-foreground" aria-hidden>
            {sortDir === "asc" ? "▲" : "▼"}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground/50" aria-hidden>
            ↕
          </span>
        )}
      </button>
    </TableHead>
  );
}
