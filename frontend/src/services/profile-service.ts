/**
 * User profile on the backend (backend/perfil.py and the calibration routes in backend/main.py).
 *
 *   GET  /perfil?email=      -> sleep hours and calibration of the account (null when missing).
 *   PUT  /perfil/sono        -> saves the hours to sleep and wake up.
 *   POST /perfil/interpretar -> reads "11 da noite", "7h30" or "1h30" from a free-text answer.
 *   GET  /calibracao         -> sample tasks with known story points.
 *   POST /calibracao         -> minutes the user would take for each one (null = skipped).
 */
import { request } from "./http";

export interface SleepDto {
  /** HH:MM */
  dormir: string;
  /** HH:MM */
  acordar: string;
}

export interface ProfileDto {
  email: string;
  sono: SleepDto | null;
  calibracao: { minutos_por_story_point: number } | null;
  minutos_por_story_point: number;
}

export interface CalibrationQuestionDto {
  titulo: string;
  objetivo: string;
  entregaveis: string;
  demonstracao: string;
}

type InterpretKind = "dormir" | "acordar" | "duracao";

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const profileService = {
  get(email: string, signal?: AbortSignal): Promise<ProfileDto> {
    return request<ProfileDto>(`/perfil?email=${encodeURIComponent(email)}`, { signal });
  },

  saveSleep(email: string, sleep: SleepDto, signal?: AbortSignal): Promise<ProfileDto> {
    return request<ProfileDto>("/perfil/sono", { method: "PUT", signal, ...json({ email, ...sleep }) });
  },

  /** "HH:MM" for dormir/acordar, minutes for duracao; null when the answer has no time in it. */
  async interpret(text: string, kind: InterpretKind, signal?: AbortSignal): Promise<string | number | null> {
    const { valor } = await request<{ valor: string | number | null }>("/perfil/interpretar", {
      method: "POST",
      signal,
      ...json({ texto: text, tipo: kind }),
    });
    return valor;
  },

  async calibrationQuestions(signal?: AbortSignal): Promise<CalibrationQuestionDto[]> {
    const { perguntas } = await request<{ perguntas: CalibrationQuestionDto[] }>("/calibracao", { signal });
    return perguntas;
  },

  async saveCalibration(answers: (number | null)[], signal?: AbortSignal): Promise<void> {
    await request<{ status: string }>("/calibracao", { method: "POST", signal, ...json(answers) });
  },
};
