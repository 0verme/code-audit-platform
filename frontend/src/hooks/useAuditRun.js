import { useEffect, useState } from "react";
import { reviewService } from "../services/reviewService";

const POLL_INTERVAL_MS = 2000;
const REPORT_NOT_READY_MESSAGE = "report not ready";

/**
 * 跟踪一次 API 审查任务：轮询任务状态，结束后拉取结构化报告。
 * taskId 为空时不发起任何请求，由调用方的 mock/api 配置决定是否使用演示数据。
 */
export function useAuditRun(taskId) {
  const [state, setState] = useState({ task: null, report: null, error: null, waitingForReport: false });

  useEffect(() => {
    setState({ task: null, report: null, error: null, waitingForReport: false });
    if (!taskId) return undefined;

    let cancelled = false;
    let timer = null;

    async function tick() {
      try {
        const task = await reviewService.getAuditTask(taskId);
        if (cancelled) return;
        if (task.status === "running" || task.status === "queued") {
          setState((current) => ({ ...current, task, waitingForReport: false }));
          timer = setTimeout(tick, POLL_INTERVAL_MS);
          return;
        }
        let report = null;
        let reportError = null;
        let waitingForReport = false;
        try {
          report = await reviewService.getAuditTaskReport(taskId);
        } catch (error) {
          if (task.status === "fail") {
            reportError = null;
          } else if (String(error?.message || "").trim().toLowerCase() === REPORT_NOT_READY_MESSAGE) {
            waitingForReport = true;
          } else {
            reportError = error;
          }
        }
        if (waitingForReport) {
          if (!cancelled) {
            setState((current) => ({ ...current, task, error: null, waitingForReport: true }));
            timer = setTimeout(tick, POLL_INTERVAL_MS);
          }
          return;
        }
        if (!cancelled) setState({ task, report, error: reportError, waitingForReport: false });
      } catch (error) {
        if (!cancelled) setState((current) => ({ ...current, error, waitingForReport: false }));
      }
    }

    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [taskId]);

  const running =
    (!!state.task && (state.task.status === "running" || state.task.status === "queued")) ||
    state.waitingForReport;
  return { ...state, running };
}
