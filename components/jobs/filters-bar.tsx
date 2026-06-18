"use client";

import { Download, Filter, RefreshCw, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDashboardStore } from "@/store/dashboard-store";
import type { ScraperSource, WorkMode } from "@/types/jobs";

const sources: ScraperSource[] = ["LinkedIn", "Naukri", "Indeed", "Company Site"];
const modes: WorkMode[] = ["Remote", "Hybrid", "Onsite"];
const ranges = [
  { label: "24 Hours", value: 1 },
  { label: "3 Days", value: 3 },
  { label: "7 Days", value: 7 },
  { label: "30 Days", value: 30 }
] as const;

export function FiltersBar({ onExport, onRefresh, isRefreshing }: { onExport: () => void; onRefresh: () => void; isRefreshing: boolean }) {
  const filters = useDashboardStore((state) => state.filters);
  const updateFilters = useDashboardStore((state) => state.updateFilters);

  function toggleSource(source: ScraperSource) {
    updateFilters({
      sources: filters.sources.includes(source)
        ? filters.sources.filter((item) => item !== source)
        : [...filters.sources, source]
    });
  }

  function toggleMode(mode: WorkMode) {
    updateFilters({
      workModes: filters.workModes.includes(mode)
        ? filters.workModes.filter((item) => item !== mode)
        : [...filters.workModes, mode]
    });
  }

  return (
    <section className="rounded-md border border-border bg-panel p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="neutral">
          <Filter className="mr-1 h-3 w-3" />
          Filters
        </Badge>
        {sources.map((source) => (
          <Button key={source} size="sm" variant={filters.sources.includes(source) ? "primary" : "secondary"} onClick={() => toggleSource(source)}>
            {source}
          </Button>
        ))}
        {modes.map((mode) => (
          <Button key={mode} size="sm" variant={filters.workModes.includes(mode) ? "primary" : "secondary"} onClick={() => toggleMode(mode)}>
            {mode}
          </Button>
        ))}
        <select
          className="h-8 rounded-md border border-border bg-background px-2 text-xs"
          value={filters.postedWithinDays ?? ""}
          onChange={(event) =>
            updateFilters({
              postedWithinDays: event.target.value ? (Number(event.target.value) as 1 | 3 | 7 | 30) : undefined
            })
          }
        >
          <option value="">Any posted time</option>
          {ranges.map((range) => (
            <option key={range.value} value={range.value}>
              Posted within {range.label}
            </option>
          ))}
        </select>
        <select
          className="h-8 rounded-md border border-border bg-background px-2 text-xs"
          value={filters.sortBy}
          onChange={(event) => updateFilters({ sortBy: event.target.value as typeof filters.sortBy })}
        >
          <option value="freshest">Freshest jobs first</option>
          <option value="oldest">Oldest jobs first</option>
          <option value="bestScore">Best GPT score first</option>
        </select>
        <label className="flex items-center gap-2 text-xs text-muted">
          GPT Score
          <input
            type="range"
            min="0"
            max="10"
            step="0.1"
            value={filters.minScore}
            onChange={(event) => updateFilters({ minScore: Number(event.target.value) })}
          />
          <span className="w-12 text-foreground">{filters.minScore}/10</span>
        </label>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="primary" onClick={onRefresh} disabled={isRefreshing}>
            <RefreshCw className={isRefreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            {isRefreshing ? "Syncing" : "Sync"}
          </Button>
          <Button size="sm" onClick={onExport}>
            <Download className="h-4 w-4" />
            CSV
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              updateFilters({
                query: "",
                sources: [],
                statuses: [],
                workModes: [],
                companies: [],
                locations: [],
                minScore: 5,
                sortBy: "freshest",
                postedWithinDays: undefined
              })
            }
          >
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        </div>
      </div>
    </section>
  );
}
