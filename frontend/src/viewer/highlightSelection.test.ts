import { describe, expect, it } from 'vitest';

import {
  excludeIssueGlobalIdsFromNeutralSelection,
  shouldPropagateSelectionClear,
} from './highlightSelection';

describe('excludeIssueGlobalIdsFromNeutralSelection', () => {
  it('keeps error elements out of the neutral selection style', () => {
    expect(
      excludeIssueGlobalIdsFromNeutralSelection(['clean-wall', 'error-wall'], ['error-wall']),
    ).toEqual(['clean-wall']);
  });
});

describe('shouldPropagateSelectionClear', () => {
  it('ignores viewer-internal clears and events after disposal', () => {
    expect(shouldPropagateSelectionClear(true, false)).toBe(false);
    expect(shouldPropagateSelectionClear(false, true)).toBe(false);
  });

  it('propagates a user-initiated clear while the viewer is active', () => {
    expect(shouldPropagateSelectionClear(false, false)).toBe(true);
  });
});
