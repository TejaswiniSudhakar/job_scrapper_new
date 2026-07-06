"use client";

import { Database, LayoutDashboard, Moon, Search, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDashboardStore } from "@/store/dashboard-store";

export function AppShell({ children }: { children: React.ReactNode }) {
  const darkMode = useDashboardStore((state) => state.darkMode);
  const toggleTheme = useDashboardStore((state) => state.toggleTheme);
  const updateFilters = useDashboardStore((state) => state.updateFilters);
  const query = useDashboardStore((state) => state.filters.query);

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-panel px-3 py-4 lg:block">
        <div className="flex items-center gap-2 px-2 pb-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-foreground text-background">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold">JobOps</div>
            <div className="text-xs text-muted">Scraper command center</div>
          </div>
        </div>
        <nav className="space-y-1">
          <Button className="w-full justify-start" variant="ghost">
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Button>
          <Button className="w-full justify-start" variant="ghost" onClick={toggleTheme}>
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {darkMode ? "Light theme" : "Dark theme"}
          </Button>
        </nav>
      </aside>

      <main className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 border-b border-border bg-panel/95 px-4 py-3 backdrop-blur">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <h1 className="text-lg font-semibold tracking-normal">Job Scraper Dashboard</h1>
              <p className="text-sm text-muted">Live pipeline view across LinkedIn, Naukri, Indeed, and company sites</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="relative min-w-64 flex-1 xl:w-80 xl:flex-none">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
                <input
                  className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Search jobs, companies, skills"
                  value={query}
                  onChange={(event) => updateFilters({ query: event.target.value })}
                />
              </label>
              <Button size="icon" aria-label="Toggle theme" onClick={toggleTheme}>
                {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </header>

        <div className="space-y-4 p-4">{children}</div>
      </main>
    </div>
  );
}
