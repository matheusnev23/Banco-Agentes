/**
 * Thin HTTP layer placeholder.
 *
 * Today every call resolves from `src/mocks`. To go live, set
 * `VITE_API_BASE_URL` and swap the `mockRequest` calls inside the services for
 * `request<T>(path, init)` — no component needs to change.
 */

export const API_BASE_URL = import.meta.env["VITE_API_BASE_URL"] ?? "/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Reserved for the future FastAPI integration. */
export async function request<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) throw new ApiError(`Request failed: ${path}`, response.status);
  return (await response.json()) as TResponse;
}

/** Simulates network latency so loading states are demonstrable. */
export function mockRequest<TResponse>(payload: TResponse, delay = 900): Promise<TResponse> {
  return new Promise((resolve) => setTimeout(() => resolve(payload), delay));
}