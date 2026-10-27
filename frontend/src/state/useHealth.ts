import { useEffect, useState } from 'react';

import { ApiError, fetchHealth, type HealthResponse } from '../api/client';

export type HealthState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'error'; readonly message: string }
  | { readonly kind: 'success'; readonly data: HealthResponse };

/** Loads backend liveness once on mount; aborts the request if the component unmounts. */
export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ kind: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((data) => setState({ kind: 'success', data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof ApiError ? error.message : 'Unexpected error';
        setState({ kind: 'error', message });
      });
    return () => controller.abort();
  }, []);

  return state;
}
