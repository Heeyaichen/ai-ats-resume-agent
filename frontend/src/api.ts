/** API client for backend communication. */

import axios from "axios";
import { UploadResponse, ScorePayload } from "./types";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});

/** Attach bearer token from MSAL to every request. */
export const setAuthToken = (token: string) => {
  apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
};

/** Upload a resume file + job description. */
export const uploadResume = async (
  file: File,
  jobDescription: string,
): Promise<UploadResponse> => {
  const form = new FormData();
  form.append("file", file);
  form.append("job_description", jobDescription);
  const { data } = await apiClient.post<UploadResponse>("/upload", form);
  return data;
};

/** Fetch score / status for a job. */
export const fetchScore = async (jobId: string): Promise<ScorePayload> => {
  const { data } = await apiClient.get<ScorePayload>(`/score/${jobId}`);
  return data;
};

/** Build the SSE stream URL for a job. */
export const sseUrl = (jobId: string): string => {
  const base = import.meta.env.VITE_API_BASE_URL || "/api";
  return `${base}/score/${jobId}/stream`;
};
