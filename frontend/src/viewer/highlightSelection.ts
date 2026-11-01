export function excludeIssueGlobalIdsFromNeutralSelection(
  selectedGlobalIds: readonly string[],
  issueGlobalIds: readonly string[],
): string[] {
  const issues = new Set(issueGlobalIds);
  return selectedGlobalIds.filter((globalId) => !issues.has(globalId));
}

export function shouldPropagateSelectionClear(
  suppressSelectionEvents: boolean,
  disposed: boolean,
): boolean {
  return !suppressSelectionEvents && !disposed;
}
