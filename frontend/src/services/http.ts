/** Shared plumbing for the service layer: every service calls the backend through `request`. */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    // fetch() rejects with a TypeError when the server is down or CORS blocks the call.
    throw new ApiError(
      `Não consegui falar com o backend em ${API_BASE_URL}. Verifique se ele está rodando (uvicorn backend.main:app).`,
      "NetworkError",
    );
  }

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

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
