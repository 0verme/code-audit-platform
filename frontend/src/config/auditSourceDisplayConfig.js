export const auditSourceDisplayRules = [
  {
    sourceType: "Local",
    prefix: "C:\\workspace\\code-audit-platform\\",
    replacement: "…\\",
  },
  {
    sourceType: "Local",
    prefix: "C:\\workspace\\",
    replacement: "本地目录\\",
  },
  {
    sourceType: "SVN",
    prefix: "svn://example.com/repos/branches/",
    replacement: "…/",
  },
  {
    sourceType: "Git",
    prefix: "https://git.example.com/group/project/",
    replacement: "…/",
  },
];
