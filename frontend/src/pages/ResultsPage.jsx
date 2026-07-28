import { useMemo } from "react";
import { Icon } from "../components/ui";
import { ChangeFilesSection } from "../components/results/ChangeFilesSection";
import {
  CheckSection,
  ConfigCheckSection,
  ConflictSection,
  OtherSourceFilesSection,
} from "../components/results/HcytBasicChecks";
import { CategoryBoard, IssuesBoard, StatusHeader } from "../components/results/HcytOverview";
import { ModuleProgressBoard, ProgressiveRunPanel, RunLogs } from "../components/results/HcytRunProgress";
import { ScheduleSection } from "../components/results/HcytScheduleSection";
import { AiSection, AssetIssuesSection } from "../components/results/SharedResultSections";
import { getSourceFiles } from "../components/SourceFileLinks";
import { useAutoOpenAccordion } from "../hooks/useAutoOpenAccordion";
import { getScriptElementId, getScriptKey, scriptAudit } from "../utils/scriptAuditPresentation";
import { PyScriptAuditSection } from "./ScriptAudit";

function mergeAuditResults(baseData, apiRows) {
  if (!apiRows?.length) return baseData;
  const grouped = {
    dws: [],
    hive: [],
    python: [],
    sbin: [],
    config: [],
    recv: [],
  };

  apiRows.forEach((row) => {
    const normalized = {
      file: row.file_name,
      rule: row.rule_name,
      level: row.level,
      msg: row.message,
    };
    if (row.category in grouped) {
      grouped[row.category].push(normalized);
    }
  });

  const totalErrors = Object.values(grouped).flat().filter((row) => row.level === "err").length;
  const totalWarnings = Object.values(grouped).flat().filter((row) => row.level === "warn").length;

  return {
    ...baseData,
    task: {
      ...baseData.task,
      errors: totalErrors,
      warnings: totalWarnings,
      status: totalErrors ? "fail" : totalWarnings ? "warn" : "pass",
    },
    ...Object.fromEntries(Object.entries(grouped).map(([key, value]) => [key, value.length ? value : baseData[key]])),
  };
}

const hasScriptFinding = (script) => {
  const audit = scriptAudit(script);
  return Boolean(audit.err || audit.warn);
};

export function ResultsPage({ d, aiEnabled, variant, reg, onJump, apiState, onViewLineage, lineageEnabled, scriptJumpRequest }) {
  const mergedData = useMemo(() => mergeAuditResults(d, apiState?.data), [d, apiState?.data]);
  const { openIds: openScriptIds, toggle: toggleScript } = useAutoOpenAccordion({
    items: mergedData.pyScripts,
    getKey: getScriptKey,
    isActionable: hasScriptFinding,
    jumpRequest: scriptJumpRequest,
    getElementId: getScriptElementId,
  });

  return (
    <div className="results-page fade-in">
      {apiState?.loading ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)" }}>正在加载审查结果...</div> : null}
      {apiState?.error ? <div className="card" style={{ padding: 14, marginBottom: "var(--gap)", borderColor: "var(--err)" }}>审查结果接口不可用，请检查任务接口配置。</div> : null}
      <ProgressiveRunPanel d={mergedData} />
      <RunLogs d={mergedData} />
      {variant !== "issues" ? <StatusHeader d={mergedData} /> : null}
      <ModuleProgressBoard d={mergedData} onJump={onJump} />
      {variant === "board" ? (
        <div className="card" style={{ padding: "var(--pad-card)", marginBottom: "var(--gap)" }}>
          <div className="subhead"><Icon name="grid" size={12} /> 检查项概览</div>
          <CategoryBoard d={mergedData} onJump={onJump} />
        </div>
      ) : null}
      {variant === "issues" ? <><StatusHeader d={mergedData} /><IssuesBoard d={mergedData} /></> : null}
      <ChangeFilesSection changes={mergedData.changes} registerRef={reg} showSummary showFileDiff />
      <ConflictSection d={mergedData} reg={reg} />
      <CheckSection id="dws" icon="db" title="DWS SQL 检查结果" rows={mergedData.dws} reg={reg} scriptMeta={mergedData.sqlChecks?.dws} />
      <CheckSection id="hive" icon="db" title="Hive SQL 检查结果" rows={mergedData.hive} reg={reg} scriptMeta={mergedData.sqlChecks?.hive} />
      <ConfigCheckSection rows={mergedData.config} files={mergedData.configFiles} sourceFiles={getSourceFiles(mergedData, "config")} reg={reg} />
      <CheckSection id="sbin" icon="terminal" title="后置脚本检查（sbin）" rows={mergedData.sbin} reg={reg} sourceFiles={getSourceFiles(mergedData, "sbin")} />
      <CheckSection id="recv" icon="download" title="收卸配置检查" rows={mergedData.recv} reg={reg} okMsg="recv_json 配置校验通过" sourceFiles={getSourceFiles(mergedData, "recv")} />
      <ScheduleSection d={mergedData} reg={reg} />
      <PyScriptAuditSection d={mergedData} reg={reg} openScriptIds={openScriptIds} onToggle={toggleScript} onViewLineage={onViewLineage} lineageEnabled={lineageEnabled} />
      <OtherSourceFilesSection d={mergedData} reg={reg} />
      <AssetIssuesSection d={mergedData} reg={reg} />
      {aiEnabled ? <AiSection d={mergedData} reg={reg} /> : null}
    </div>
  );
}
