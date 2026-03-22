import axios from "axios";
import type { AuthResponse, User } from "@/types";
import { logToFile } from "./logger";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const API_BASE_URL = API_URL ? `${API_URL}/api` : "/api";

export const AUTH_TOKEN_KEY = "sigmacloud_auth_token";

let authToken: string | null = null;

function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return authToken;
  }

  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 120000,
});

export function setAuthToken(token: string | null) {
  authToken = token;

  if (typeof window !== "undefined") {
    if (token) {
      window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  }

  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

if (typeof window === "undefined") {
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      const msg = error?.message || "Unknown error";
      const url = error?.config?.url || "unknown";
      const method = error?.config?.method || "unknown";
      const status = error?.response?.status || "no-status";
      logToFile(`API error: [${method}] ${url} status=${status} msg=${msg}`, "error");
      return Promise.reject(error);
    }
  );
}

api.interceptors.request.use((config) => {
  const token = authToken || readStoredToken();

  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export const datasetsAPI = {
  upload: (formData: FormData) =>
    api.post("/upload-dataset", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  list: () => api.get("/datasets"),
  get: (id: number) => api.get(`/datasets/${id}`),
  getAnalysis: (id: number) => api.get(`/datasets/${id}/analysis`),
  delete: (id: number) => api.delete(`/datasets/${id}`),
  loadExample: (key: string) => api.post(`/load-example/${key}`),
  listExamples: () => api.get("/example-datasets"),
};

export const trainingAPI = {
  train: (config: {
    dataset_id: number;
    target_column: string;
    task_type?: string;
    mode?: string;
    models_to_train?: string[];
    tuning_params?: Record<string, Record<string, number | string>>;
    test_size?: number;
    cv_folds?: number;
  }) => api.post("/train-model", config),
  recommend: (config: {
    dataset_id: number;
    target_column: string;
    task_type?: string;
  }) => api.post("/training-recommendation", config),
  getStatus: (jobId: string) => api.get(`/training-status/${jobId}`),
  listJobs: () => api.get("/training-jobs"),
};

export const modelsAPI = {
  list: (jobId?: string) => api.get("/models", { params: jobId ? { job_id: jobId } : {} }),
  get: (id: number) => api.get(`/models/${id}`),
  deploy: (id: number) => api.post(`/models/${id}/deploy`),
  undeploy: (id: number) => api.post(`/models/${id}/undeploy`),
  download: (id: number) => (API_URL ? `${API_URL}/api/models/${id}/download` : `/api/models/${id}/download`),
  delete: (id: number) => api.delete(`/models/${id}`),
  listDeployed: () => api.get("/deployed-models"),
};

export const metricsAPI = {
  getJobMetrics: (jobId: string) => api.get(`/metrics/${jobId}`),
  getDashboardSummary: () => api.get("/dashboard/summary"),
};

export const predictionsAPI = {
  predict: (modelId: number, features: Record<string, unknown>) =>
    api.post("/predict", { model_id: modelId, features }),
};

export const authAPI = {
  googleSignIn: (credential: string) => api.post<AuthResponse>("/auth/google", { credential }),
  me: () => api.get<User>("/auth/me"),
};

export default api;
