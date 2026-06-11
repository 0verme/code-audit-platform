import { useEffect, useState } from "react";
import { reviewService } from "../services/reviewService";

const POLL_INTERVAL_MS = 2000;

/**
 * 跟踪一次真实审查任务：轮询任务状态，结束后拉取结构化报告。
 * taskId 为空时不发起任何请求（纯原型 / mock 模式）。
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
        try {
          report = await reviewService.getAuditTaskReport(taskId);
        } catch {
          // 报告未生成（任务失败），保留 task.error 供页面展示
        }
        if (!cancelled) setState({ task, report, error: null });
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
