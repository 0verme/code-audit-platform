// Deployment-specific path masking is supplied by the backend at runtime.
// Do not embed local, SVN, or Git prefixes in the shipped frontend.
export const auditSourceDisplayRules = [];

export function applyAuditSourceDisplayRules(rules) {
  const safeRules = Array.isArray(rules)
    ? rules.filter((rule) => (
      rule
      && typeof rule.sourceType === "string"
      && typeof rule.prefix === "string"
      && rule.prefix.trim()
      && (rule.replacement == null || typeof rule.replacement === "string")
    ))
    : [];

  auditSourceDisplayRules.splice(0, auditSourceDisplayRules.length, ...safeRules);
}
