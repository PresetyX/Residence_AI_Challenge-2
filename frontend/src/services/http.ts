/**
 * Shared plumbing for the service layer.
 *
 * Every service checks USE_MOCKS: when true it answers from the in-browser mocks,
 * otherwise it calls the backend through `request`. Swapping to the real backend is
 * a matter of setting NEXT_PUBLIC_USE_MOCKS=false and NEXT_PUBLIC_API_URL.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

/**
 * The project planner (POST /projetos) is the one backend route that exists today, so it
 * has its own switch: on by default, even while auth, chat and calendar stay on mocks.
 * Set NEXT_PUBLIC_USE_PLANNER_API=false to plan projects with the in-browser mock.
 */
export const USE_PLANNER_API = process.env.NEXT_PUBLIC_USE_PLANNER_API !== "false";

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
      (await readErrorDetail(response)) ??
        "Não foi possível concluir a solicitação. Tente novamente.",
      "HttpError",
      response.status,
    );
  }

  return (response.status === 204 ? undefined : await response.json()) as T;
}

/**
 * FastAPI errors come as { detail: "..." } (HTTPException) or
 * { detail: [{ msg: "..." }] } (validation). Returns null when the body has neither.
 */
export async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((item) => (item as { msg?: unknown })?.msg)
        .filter((msg): msg is string => typeof msg === "string")
        .map((msg) => msg.replace(/^Value error, /, ""));
      if (messages.length) return messages.join(" ");
    }
  } catch {
    // Not JSON: fall back to the generic message.
  }
  return null;
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
