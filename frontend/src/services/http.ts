/**
 * Shared plumbing for the service layer.
 *
 * Every service checks USE_MOCKS: when true it answers from the in-browser mocks,
 * otherwise it calls the backend through `request`. Swapping to the real backend is
 * a matter of setting NEXT_PUBLIC_USE_MOCKS=false and NEXT_PUBLIC_API_URL.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly kind: string = "ApiError",
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });

  if (!response.ok) {
    throw new ApiError(
      "Não foi possível concluir a solicitação. Tente novamente.",
      "HttpError",
      response.status,
    );
  }

  return (response.status === 204 ? undefined : await response.json()) as T;
}

/** Simulated network latency for the mocks. Rejects with AbortError when aborted. */
export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
