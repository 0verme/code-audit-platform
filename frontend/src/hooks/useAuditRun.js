import { useEffect, useState } from "react";
import { reviewService } from "../services/reviewService";

const POLL_INTERVAL_MS = 2000;

/**
 * 跟踪一次 API 审查任务：轮询任务状态，结束后拉取结构化报告。
 * taskId 为空时不发起任何请求，由调用方的 mock/api 配置决定是否使用演示数据。
 */
export function useAuditRun(taskId) {
  const [state, setState] = useState({ task: null, report: null, error: null });

  useEffect(() => {
    setState({ task: null, report: null, error: null });
    if (!taskId) return undefined;

    let cancelled = false;
    let timer = null;

    async function tick() {
      try {
        const task = await reviewService.getAuditTask(taskId);
        if (cancelled) return;
        if (task.status === "running" || task.status === "queued") {
          setState((current) => ({ ...current, task }));
          timer = setTimeout(tick, POLL_INTERVAL_MS);
          return;
        }
        let report = null;
        let reportError = null;
        try {
          report = await reviewService.getAuditTaskReport(taskId);
        } catch (error) {
          if (task.status !== "fail") {
            reportError = error;
          }
        }
        if (!cancelled) setState({ task, report, error: reportError });
      } catch (error) {
        if (!cancelled) setState((current) => ({ ...current, error }));
      }
    }

    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [taskId]);

  const running = !!state.task && (state.task.status === "running" || state.task.status === "queued");
  return { ...state, running };
}
