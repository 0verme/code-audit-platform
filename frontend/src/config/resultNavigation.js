import {
  getPythonIssueRows,
  getScheduleIssueRows,
} from "../utils/hcytResultPresentation.js";
import {
  getNupsChanges,
  getNupsPyScripts,
  getNupsSqlChecks,
} from "../utils/nupsResultPresentation.js";
import { getSourceFiles } from "../utils/sourceFilePresentation.js";

const rowsWithSourceFiles = (data, rows, section) => [
  ...(Array.isArray(rows) ? rows : []),
  ...getSourceFiles(data, section),
];

const ASSET_ISSUES_NAV = {
  id: "asset-issues",
  label: "资产问题",
  icon: "link",
  get: (data) => data?.assetIssues || [],
};

export const RESULT_NAVIGATION = {
  hcyt: [
    { id: "overview", label: "概览", icon: "layers" },
    {
      id: "changes",
      label: "变更文件",
      icon: "git",
      get: (data) => data?.changes || [],
      neutral: true,
    },
    {
      id: "conflict",
      label: "trunk 冲突",
      icon: "conflict",
      get: (data) => data?.conflicts || [],
    },
    {
      id: "dws",
      label: "DWS SQL",
      icon: "db",
      get: (data) => rowsWithSourceFiles(data, data?.dws, "dws"),
    },
    {
      id: "hive",
      label: "Hive SQL",
      icon: "db",
      get: (data) => rowsWithSourceFiles(data, data?.hive, "hive"),
    },
    {
      id: "config",
      label: "配置文件",
      icon: "cog",
      get: (data) => rowsWithSourceFiles(data, data?.config, "config"),
    },
    {
      id: "sbin",
      label: "后置脚本",
      icon: "terminal",
      get: (data) => rowsWithSourceFiles(data, data?.sbin, "sbin"),
    },
    {
      id: "recv",
      label: "收卸配置",
      icon: "download",
      get: (data) => rowsWithSourceFiles(data, data?.recv, "recv"),
    },
    {
      id: "schedule",
      label: "调度表检查",
      icon: "grid",
      get: (data) =>
        rowsWithSourceFiles(data, getScheduleIssueRows(data), "schedule"),
    },
    {
      id: "python",
      label: "Python 脚本",
      icon: "python",
      get: (data) =>
        rowsWithSourceFiles(data, getPythonIssueRows(data), "python"),
      neutral: true,
    },
    {
      id: "other-files",
      label: "其他审计文件",
      icon: "file",
      get: (data) => getSourceFiles(data, "other-files"),
      neutral: true,
    },
    ASSET_ISSUES_NAV,
  ],
  "fine-report": [
    { id: "overview", label: "概览", icon: "layers" },
    {
      id: "changes",
      label: "变更文件",
      icon: "git",
      get: (data) => data?.changes || [],
      neutral: true,
    },
    {
      id: "menu",
      label: "目录",
      icon: "folder",
      get: (data) => data?.menu?.rows || [],
      neutral: true,
    },
    {
      id: "authority",
      label: "权限",
      icon: "shield",
      get: (data) => data?.authority?.rows || [],
      neutral: true,
    },
    {
      id: "reports",
      label: "报表检查",
      icon: "grid",
      get: (data) => data?.reports || [],
      neutral: true,
    },
    ASSET_ISSUES_NAV,
  ],
  nups: [
    { id: "overview", label: "概览", icon: "layers" },
    {
      id: "changes",
      label: "变更文件",
      icon: "git",
      get: (data) => getNupsChanges(data),
      neutral: true,
    },
    {
      id: "conflict",
      label: "冲突文件",
      icon: "conflict",
      get: (data) => data?.conflicts || [],
      neutral: true,
    },
    {
      id: "nups-sql",
      label: "NUPS SQL",
      icon: "db",
      get: (data) => getNupsSqlChecks(data),
      neutral: true,
    },
    {
      id: "nups-py",
      label: "加工程序",
      icon: "python",
      get: (data) => getNupsPyScripts(data),
      neutral: true,
    },
    ASSET_ISSUES_NAV,
  ],
};

export function getResultNavigation(workflow) {
  return RESULT_NAVIGATION[workflow] || RESULT_NAVIGATION.hcyt;
}
