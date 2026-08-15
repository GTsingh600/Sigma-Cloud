import axios from "axios";
import type { AuthResponse, HealthStatus, User } from "@/types";
import { logToFile } from "./logger";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const API_BASE_URL = API_URL ? `${API_URL}/api` : "/api";

export const AUTH_TOKEN_KEY = "sigmacloud_auth_token";

/**
 * Free hosting tiers sleep when idle and take up to a minute to wake, so the
 * default timeout is deliberately generous. Training calls get longer still.
 */
export const COLD_START_TIMEOUT_MS = 90_000;

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
  timeout: COLD_START_TIMEOUT_MS,
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

/** Pull a readable message out of an axios error, including 422 detail objects. */
export function describeApiError(error: unknown, fallback = "Something went wrong"): string {
  const detail = (error as any)?.response?.data?.detail;

  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const missing: string[] | undefined = detail.missing_features;
    return missing?.length ? `${detail.message} (${missing.join(", ")})` : detail.message;
  }
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;

  const code = (error as any)?.code;
  if (code === "ECONNABORTED") {
    return "The server took too long to respond. It may still be waking up - try again.";
  }
  if ((error as any)?.message === "Network Error") {
    return "Could not reach the API. Check that the backend is running.";
  }

  return (error as any)?.message || fallback;
}

export const healthAPI = {
  check: () => api.get<HealthStatus>("/health", { timeout: COLD_START_TIMEOUT_MS }),
};

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
  delete: (id: number) => api.delete(`/models/${id}`),
  listDeployed: () => api.get("/deployed-models"),
  getFeatures: (id: number) => api.get(`/models/${id}/features`),

  /**
   * Downloads through XHR rather than a plain <a href>.
   *
   * The endpoint requires an Authorization header, which a link element cannot
   * send - the old anchor-based download always came back 401.
   */
  download: async (id: number, modelName: string) => {
    const response = await api.get(`/models/${id}/download`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${modelName.replace(/\s+/g, "_")}_${id}.joblib`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
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
