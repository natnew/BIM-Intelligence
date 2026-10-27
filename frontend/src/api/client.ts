/**
 * Typed API client. Hand-written for the health endpoint only; domain types
 * (Finding, Requirement, Explanation) will be generated from the backend's
 * Pydantic JSON Schema (ADR-014) once those schemas exist.
 */

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';

export type LLMMode = 'live' | 'replay' | 'off';

export interface LibraryVersions {
  readonly ifcopenshell: string | null;
  readonly ifctester: string | null;
}

export interface HealthResponse {
  readonly status: string;
  readonly version: string;
  readonly llm_mode: LLMMode;
  readonly llm_model: string;
  readonly llm_configured: boolean;
  readonly libraries: LibraryVersions;
}

export class ApiError extends Error {
  readonly status: number | undefined;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/health`, { signal: signal ?? null });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    throw new ApiError('Backend unreachable. Is the API running on port 8000?');
  }
  if (!response.ok) {
    throw new ApiError(`Health check failed (${response.status})`, response.status);
  }
  return (await response.json()) as HealthResponse;
}
