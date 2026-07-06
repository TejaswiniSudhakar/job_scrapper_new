"use client";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import { useCallback, useMemo, useRef } from "react";
import { AllCommunityModule, ModuleRegistry, type ColDef, type GridApi, type GridReadyEvent, type RowClickedEvent, type PostSortRowsParams } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatRelativeTime } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";
import type { Job, JobStatus } from "@/types/jobs";

const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];

ModuleRegistry.registerModules([AllCommunityModule]);

export function JobGrid({ jobs }: { jobs: Job[] }) {
  const gridRef = useRef<GridApi<Job> | null>(null);
  const jobOrderRef = useRef<Map<string, number>>(new Map());
  const selectJob = useDashboardStore((state) => state.selectJob);
  const updateStatus = useDashboardStore((state) => state.updateStatus);
  const pushToast = useDashboardStore((state) => state.pushToast);
  const darkMode = useDashboardStore((state) => state.darkMode);

  // Keep a ref of the intended row order from the parent
  useMemo(() => {
    const map = new Map<string, number>();
    jobs.forEach((job, i) => map.set(job.id, i));
    jobOrderRef.current = map;
  }, [jobs]);

  const columnDefs = useMemo<ColDef<Job>[]>(
    () => [
      {
        headerName: "Job Title",
        field: "jobTitle",
        pinned: "left",
        minWidth: 240,
        checkboxSelection: true,
        cellRenderer: ({ data, value }: { data: Job; value: string }) => (
          <button className="text-left font-medium text-foreground hover:underline" onClick={() => selectJob(data)}>
            {value}
          </button>
        )
      },
      { headerName: "Company", field: "company", minWidth: 160 },
      {
        headerName: "GPT Score",
        field: "gptRelevanceScore",
        minWidth: 105,
        cellRenderer: ({ value }: { value: number }) => (
          <span className={value >= 8 ? "font-semibold text-teal-600" : "font-medium"}>{value.toFixed(1)}/10</span>
        )
      },
      {
        headerName: "Posted ago",
        field: "postedTime",
        minWidth: 110,
        valueFormatter: ({ value }) => formatRelativeTime(value)
      },
      {
        headerName: "Experience",
        field: "experienceRequired",
        minWidth: 115,
        comparator: compareExperience
      },
      {
        headerName: "Salary",
        field: "salary",
        minWidth: 120,
        valueFormatter: ({ value }) => value || "Not mentioned"
      },
      { headerName: "Employment Type", field: "employmentType", minWidth: 125 },
      { headerName: "Source", field: "source", minWidth: 105, filter: true },
      {
        headerName: "Scraped",
        field: "scrapedTime",
        minWidth: 110,
        valueFormatter: ({ value }) => formatRelativeTime(value)
      },
      { headerName: "Location", field: "location", minWidth: 180 },
      {
        headerName: "Match %",
        field: "matchPercentage",
        minWidth: 120,
        valueFormatter: ({ value }) => `${value}%`
      },
      {
        headerName: "Apply",
        field: "applyLink",
        minWidth: 120,
        cellRenderer: ({ data }: { data: Job }) => (
          <Button
            size="sm"
            variant="primary"
            onClick={(event) => {
              event.stopPropagation();
              updateStatus(data.id, "APPLIED");
              window.open(data.applyLink, "_blank", "noopener,noreferrer");
              pushToast({
                tone: "info",
                title: "Marked as applied",
                description: `${data.jobTitle} at ${data.company}`
              });
            }}
          >
            <ExternalLink className="h-3 w-3" />
            Apply
          </Button>
        )
      },
      {
        headerName: "Status",
        field: "status",
        minWidth: 140,
        cellRenderer: ({ value }: { value: JobStatus }) => <StatusBadge status={value} />
      },
      { headerName: "Notes", field: "notes", minWidth: 260, editable: true },
      {
        headerName: "Quick Actions",
        minWidth: 190,
        pinned: "right",
        cellRenderer: ({ data }: { data: Job }) => (
          <select
            className="h-8 rounded-md border border-border bg-background px-2 text-xs"
            value={data.status}
            onChange={(event) => updateStatus(data.id, event.target.value as JobStatus)}
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        )
      }
    ],
    [pushToast, selectJob, updateStatus]
  );

  function onGridReady(event: GridReadyEvent<Job>) {
    gridRef.current = event.api;
  }

  function onRowClicked(event: RowClickedEvent<Job>) {
    if (event.data) selectJob(event.data);
  }

  const enforceExternalOrder = useCallback((params: PostSortRowsParams<Job>) => {
    const orderMap = jobOrderRef.current;
    params.nodes.sort((a, b) => {
      const idxA = orderMap.get(a.data?.id ?? "") ?? Number.MAX_SAFE_INTEGER;
      const idxB = orderMap.get(b.data?.id ?? "") ?? Number.MAX_SAFE_INTEGER;
      return idxA - idxB;
    });
  }, [jobs]);

  function getRowClasses(data?: Job) {
    return [data?.status === "APPLIED" ? "applied-job-row" : "", data?.isNew ? "new-job-row" : ""]
      .filter(Boolean)
      .join(" ");
  }

  return (
    <div className={darkMode ? "ag-theme-quartz-dark h-[620px]" : "ag-theme-quartz h-[620px]"}>
      <AgGridReact<Job>
        rowData={jobs}
        columnDefs={columnDefs}
        theme="legacy"
        defaultColDef={{
          sortable: false,
          filter: true,
          resizable: true,
          floatingFilter: true
        }}
        rowSelection="multiple"
        animateRows
        suppressScrollOnNewData
        getRowId={({ data }) => data.id}
        pagination
        paginationPageSize={50}
        rowBuffer={20}
        suppressCellFocus
        postSortRows={enforceExternalOrder}
        onGridReady={onGridReady}
        onRowClicked={onRowClicked}
        getRowClass={({ data }) => getRowClasses(data)}
      />
    </div>
  );
}

function compareExperience(valueA?: string, valueB?: string) {
  const expA = parseExperienceRange(valueA);
  const expB = parseExperienceRange(valueB);

  if (expA.min !== expB.min) return expA.min - expB.min;
  if (expA.max !== expB.max) return expA.max - expB.max;
  return expA.label.localeCompare(expB.label);
}

function parseExperienceRange(value?: string) {
  const label = value || "";
  const numbers = label.match(/\d+(?:\.\d+)?/g)?.map(Number) ?? [];
  const min = numbers[0] ?? Number.MAX_SAFE_INTEGER;
  const max = numbers[1] ?? min;

  return { label, min, max };
}
