import type {
  ArielExaminerResult,
  ArielMemory,
  AdminUserDetail,
  AdminUserListResponse,
  AdminAuditLogResponse,
  AdminConceptQualityResponse,
  AdminParserPreview,
  AdminRegenerationResponse,
  AdminTextbookDetail,
  AdminTextbookListResponse,
  AdminUserAnalytics,
  CommandCenterDashboard,
  CurrentConceptResponse,
  DashboardResponse,
  ChapterConcept,
  AuthResponse,
  DirectUploadUrlResponse,
  DocumentUploadResponse,
  MCQResponse,
  QuizAnswers,
  QuizSubmissionResult,
  Subject,
  SignupPayload,
  ThemeKey,
  TutorAnswer,
  TutorLessonResponse,
  UserSettings
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export function clearClientAuthState(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem("user");
  window.localStorage.removeItem("auth_user");
  window.localStorage.removeItem("access_token");
  window.localStorage.removeItem("refresh_token");
  window.sessionStorage.removeItem("user");
  window.sessionStorage.removeItem("auth_user");
  window.sessionStorage.removeItem("access_token");
  window.sessionStorage.removeItem("refresh_token");
  window.sessionStorage.removeItem("signup_welcome");
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1]) : null;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET";
  const csrfToken = ["GET", "HEAD", "OPTIONS"].includes(method) ? null : getCookie("csrftoken");

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      credentials: "include",
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        ...init?.headers
      }
    });
  } catch (caught) {
    const detail = caught instanceof Error ? caught.message : "Unknown network error";
    throw new Error(`Could not reach ${API_BASE_URL}${path}. ${detail}`);
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errorBody = (await response.json()) as { detail?: string; error?: string; errors?: unknown };
      message = errorBody.detail ?? errorBody.error ?? formatValidationErrors(errorBody.errors ?? errorBody) ?? message;
    } catch {
      // Keep the status-based message when the backend does not return JSON.
    }

    if (response.status === 401) {
      throw new Error("Your session has expired. Please log in again to continue studying.");
    }

    if (response.status === 403 && message === `Request failed with status ${response.status}`) {
      throw new Error("Your session could not be verified. Refresh the page or log in again.");
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function ensureCsrfCookie(): Promise<void> {
  await requestJson<{ detail: string }>("/auth/csrf/");
}

function formatValidationErrors(errors: unknown): string | null {
  if (!errors) {
    return null;
  }

  if (typeof errors === "string") {
    return errors;
  }

  if (Array.isArray(errors)) {
    return errors.map((error) => formatValidationErrors(error)).filter(Boolean).join(" ");
  }

  try {
    if (typeof errors === "object") {
      return Object.entries(errors)
        .map(([field, value]) => {
          const formattedValue = formatValidationErrors(value);
          if (!formattedValue) {
            return null;
          }
          return field === "non_field_errors" ? formattedValue : `${field}: ${formattedValue}`;
        })
        .filter(Boolean)
        .join(" ");
    }

    return JSON.stringify(errors);
  } catch {
    return "The backend rejected the request data.";
  }
}

export async function getProgressDashboard(subjectId?: number): Promise<DashboardResponse> {
  return requestJson<DashboardResponse>(`/dashboard/${subjectQuery(subjectId)}`);
}

export async function getCommandCenterDashboard(): Promise<CommandCenterDashboard> {
  return requestJson<CommandCenterDashboard>("/admin/command-center/");
}

export async function getAdminUserAnalytics(): Promise<AdminUserAnalytics> {
  return requestJson<AdminUserAnalytics>("/admin/analytics/users/");
}

export async function getAdminUsers(params: { q?: string; status?: string; role?: string } = {}): Promise<AdminUserListResponse> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.status && params.status !== "all") {
    query.set("status", params.status);
  }
  if (params.role && params.role !== "all") {
    query.set("role", params.role);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<AdminUserListResponse>(`/admin/users/${suffix}`);
}

export async function getAdminUserDetail(userId: number): Promise<AdminUserDetail> {
  return requestJson<AdminUserDetail>(`/admin/users/${userId}/`);
}

export async function setAdminUserActive(userId: number, isActive: boolean): Promise<AdminUserDetail> {
  return requestJson<AdminUserDetail>(`/admin/users/${userId}/${isActive ? "reactivate" : "deactivate"}/`, {
    method: "POST"
  });
}

export async function getAdminTextbooks(params: { q?: string; status?: string; confidence?: string } = {}): Promise<AdminTextbookListResponse> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.status && params.status !== "all") {
    query.set("status", params.status);
  }
  if (params.confidence && params.confidence !== "all") {
    query.set("confidence", params.confidence);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<AdminTextbookListResponse>(`/admin/textbooks/${suffix}`);
}

export async function getAdminTextbookDetail(documentId: number): Promise<AdminTextbookDetail> {
  return requestJson<AdminTextbookDetail>(`/admin/textbooks/${documentId}/`);
}

export async function getAdminTextbookParserPreview(documentId: number): Promise<AdminParserPreview> {
  return requestJson<AdminParserPreview>(`/admin/textbooks/${documentId}/parser-preview/`);
}

export async function reprocessAdminTextbook(documentId: number, forceResetProgress: boolean): Promise<{ detail: string }> {
  return requestJson<{ detail: string }>(`/admin/textbooks/${documentId}/reprocess/`, {
    method: "POST",
    body: JSON.stringify({ confirm: true, force_reset_progress: forceResetProgress })
  });
}

export async function deleteAdminTextbook(documentId: number): Promise<void> {
  await requestJson<void>(`/admin/textbooks/${documentId}/?confirm=true`, {
    method: "DELETE"
  });
}

export async function getAdminConceptQuality(
  params: { q?: string; documentId?: string; chapterId?: string; issue?: string } = {}
): Promise<AdminConceptQualityResponse> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.documentId) {
    query.set("document_id", params.documentId);
  }
  if (params.chapterId) {
    query.set("chapter_id", params.chapterId);
  }
  if (params.issue && params.issue !== "all") {
    query.set("issue", params.issue);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<AdminConceptQualityResponse>(`/admin/quality/concepts/${suffix}`);
}

export async function regenerateAdminConceptMcqs(conceptId: number): Promise<AdminRegenerationResponse> {
  return requestJson<AdminRegenerationResponse>(`/admin/quality/concepts/${conceptId}/regenerate-mcqs/`, {
    method: "POST",
    body: JSON.stringify({ confirm: true })
  });
}

export async function regenerateAdminConceptTutor(conceptId: number): Promise<AdminRegenerationResponse> {
  return requestJson<AdminRegenerationResponse>(`/admin/quality/concepts/${conceptId}/regenerate-tutor/`, {
    method: "POST",
    body: JSON.stringify({ confirm: true })
  });
}

export async function getAdminAuditLogs(
  params: { q?: string; action?: string; targetType?: string } = {}
): Promise<AdminAuditLogResponse> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.action) {
    query.set("action", params.action);
  }
  if (params.targetType) {
    query.set("target_type", params.targetType);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<AdminAuditLogResponse>(`/admin/audit-logs/${suffix}`);
}

export async function getCurrentUser(): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/auth/me/");
}

export async function getUserSettings(): Promise<UserSettings> {
  return requestJson<UserSettings>("/auth/settings/");
}

export async function updateUserSettings(theme: ThemeKey): Promise<UserSettings> {
  return requestJson<UserSettings>("/auth/settings/", {
    method: "PATCH",
    body: JSON.stringify({ theme })
  });
}

export async function signup(payload: SignupPayload): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/auth/signup/", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const result = await requestJson<AuthResponse>("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
  try {
    await ensureCsrfCookie();
  } catch {
    // The next unsafe request can request CSRF again. Login itself has already succeeded.
  }
  return result;
}

export async function logout(): Promise<void> {
  await ensureCsrfCookie();
  try {
    await requestJson<{ detail: string }>("/auth/logout/", { method: "POST" });
  } finally {
    clearClientAuthState();
  }
}

export async function getSubjects(): Promise<Subject[]> {
  return requestJson<Subject[]>("/subjects/");
}

export async function createSubject(name: string): Promise<Subject> {
  return requestJson<Subject>("/subjects/", {
    method: "POST",
    body: JSON.stringify({ name })
  });
}

export async function deleteSubject(subjectId: number): Promise<void> {
  await requestJson<void>(`/subjects/${subjectId}/`, {
    method: "DELETE"
  });
}

export async function uploadDocument(title: string, subjectId: number | null, file: File): Promise<DocumentUploadResponse> {
  try {
    return await uploadDocumentDirectly(title, subjectId, file);
  } catch (caught) {
    if (isDirectUploadConfigurationError(caught)) {
      return uploadDocumentThroughDjango(title, subjectId, file);
    }
    throw caught;
  }
}

async function uploadDocumentDirectly(title: string, subjectId: number | null, file: File): Promise<DocumentUploadResponse> {
  if (!getCookie("csrftoken")) {
    await ensureCsrfCookie();
  }

  const contentType = file.type || "application/pdf";
  const uploadConfig = await requestJson<DirectUploadUrlResponse>("/documents/direct-upload-url/", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      content_type: contentType,
      file_size_bytes: file.size
    })
  });

  const uploadResponse = await fetch(uploadConfig.upload_url, {
    method: uploadConfig.method,
    headers: uploadConfig.headers,
    body: file
  });

  if (!uploadResponse.ok) {
    throw new Error(`R2 upload failed with status ${uploadResponse.status}`);
  }

  return requestJson<DocumentUploadResponse>("/documents/complete-direct-upload/", {
    method: "POST",
    body: JSON.stringify({
      title,
      subject: subjectId,
      object_key: uploadConfig.object_key,
      filename: file.name,
      content_type: contentType,
      file_size_bytes: file.size
    })
  });
}

async function uploadDocumentThroughDjango(title: string, subjectId: number | null, file: File): Promise<DocumentUploadResponse> {
  if (!getCookie("csrftoken")) {
    await ensureCsrfCookie();
  }

  const csrfToken = getCookie("csrftoken");
  const formData = new FormData();
  formData.append("title", title);
  if (subjectId) {
    formData.append("subject", String(subjectId));
  }
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/documents/`, {
      method: "POST",
      cache: "no-store",
      credentials: "include",
      headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
      body: formData
    });
  } catch (caught) {
    const detail = caught instanceof Error ? caught.message : "Unknown network error";
    throw new Error(`Could not reach ${API_BASE_URL}/documents/. ${detail}`);
  }

  if (!response.ok) {
    let message = `Upload failed with status ${response.status}`;
    try {
      const errorBody = (await response.json()) as { detail?: string; error?: string; errors?: unknown };
      message = errorBody.detail ?? errorBody.error ?? formatValidationErrors(errorBody.errors ?? errorBody) ?? message;
    } catch {
      // Keep the status-based message when the backend/proxy does not return JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<DocumentUploadResponse>;
}

function isDirectUploadConfigurationError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("Direct uploads are not configured yet.");
}

export async function deleteDocument(documentId: number): Promise<void> {
  await requestJson<void>(`/documents/${documentId}/`, {
    method: "DELETE"
  });
}

function subjectQuery(subjectId?: number): string {
  return subjectId ? `?subject=${subjectId}` : "";
}

export async function getCurrentConcept(documentId: string, subjectId?: number): Promise<CurrentConceptResponse> {
  return requestJson<CurrentConceptResponse>(`/documents/${documentId}/current-concept/${subjectQuery(subjectId)}`);
}

export async function getChapterConcepts(chapterId: number, subjectId: number): Promise<ChapterConcept[]> {
  return requestJson<ChapterConcept[]>(`/chapters/${chapterId}/concepts/?subject=${subjectId}`);
}

export async function requestTutorLesson(documentId: string, subjectId?: number): Promise<TutorLessonResponse> {
  return requestJson<TutorLessonResponse>(`/documents/${documentId}/tutor/current/${subjectQuery(subjectId)}`, {
    method: "POST"
  });
}

export async function askTutorQuestion(conceptId: number, question: string, subjectId?: number): Promise<TutorAnswer> {
  return requestJson<TutorAnswer>("/tutor/ask/", {
    method: "POST",
    body: JSON.stringify({ concept_id: conceptId, question, subject_id: subjectId ?? null })
  });
}

export async function submitArielToExaminer(conceptId: number, subjectId?: number): Promise<ArielExaminerResult> {
  return requestJson<ArielExaminerResult>("/student-ai/examiner/check/", {
    method: "POST",
    body: JSON.stringify({ concept_id: conceptId, subject_id: subjectId ?? null })
  });
}

export async function teachArielMemory(conceptId: number, taughtContent: string, subjectId?: number): Promise<ArielMemory> {
  return requestJson<ArielMemory>("/student-ai/memory/teach/", {
    method: "POST",
    body: JSON.stringify({
      concept_id: conceptId,
      subject_id: subjectId ?? null,
      taught_content: taughtContent,
      initial_mastery_score: 85
    })
  });
}

export async function getCurrentMcqs(documentId: string): Promise<MCQResponse> {
  return requestJson<MCQResponse>(`/documents/${documentId}/mcqs/current/`);
}

export async function submitCurrentMcqs(
  documentId: string,
  answers: QuizAnswers
): Promise<QuizSubmissionResult> {
  return requestJson<QuizSubmissionResult>(`/documents/${documentId}/mcqs/current/submit/`, {
    method: "POST",
    body: JSON.stringify({ answers })
  });
}

export async function restartCurrentConcept(documentId: string): Promise<void> {
  await requestJson<{ detail: string }>(`/documents/${documentId}/restart-current-concept/`, {
    method: "POST"
  });
}

export async function restartChapter(chapterId: number): Promise<void> {
  await requestJson<{ detail: string }>(`/chapters/${chapterId}/restart/`, {
    method: "POST"
  });
}

export async function restartDocument(documentId: number): Promise<void> {
  await requestJson<{ detail: string }>(`/documents/${documentId}/restart/`, {
    method: "POST"
  });
}
