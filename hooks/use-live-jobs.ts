"use client";

import { useEffect } from "react";
import { realtimeClient } from "@/lib/realtime/job-events";
import { useDashboardStore } from "@/store/dashboard-store";

export function useLiveJobs() {
  const addJob = useDashboardStore((state) => state.addJob);
  const pushToast = useDashboardStore((state) => state.pushToast);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_ENABLE_MOCK_REALTIME !== "true") return;

    return realtimeClient.subscribe((event) => {
      if (event.type === "job.created") {
        addJob(event.payload);
      }

      if (event.type === "scraper.failed") {
        pushToast({
          tone: "danger",
          title: `${event.payload.source} failed`,
          description: "Check scraper logs and browser session state."
        });
      }

      if (event.type === "scoring.completed") {
        pushToast({
          tone: "info",
          title: "GPT scoring complete",
          description: `Job scored ${event.payload.score}% relevance.`
        });
      }
    });
  }, [addJob, pushToast]);
}
