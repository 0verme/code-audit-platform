export function getHomePathFeedbackState({
  path,
  detectedSource,
  detectedWorkflow,
  hasValidated,
  submitError,
}) {
  const hasPath = Boolean(String(path || "").trim());
  const hasMatch = hasPath && detectedSource.valid && Boolean(detectedWorkflow);
  const showSourceError = hasValidated && hasPath && !detectedSource.valid;
  const showWorkflowError = hasValidated
    && hasPath
    && detectedSource.valid
    && !detectedWorkflow;

  return {
    hasMatch,
    showInputDetection: hasPath && (detectedSource.valid || hasValidated),
    showRouteCard: hasMatch,
    showSourceError,
    showWorkflowError,
    showSubmitError: Boolean(submitError) && !showSourceError && !showWorkflowError,
  };
}
