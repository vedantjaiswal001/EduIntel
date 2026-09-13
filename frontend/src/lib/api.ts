import axios from "axios";

// Single axios instance. Base URL is relative so the Vite dev proxy (and the
// nginx reverse proxy in production) forward /api to the backend.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
  timeout: 60000,
});

// ---- shared types ----
export interface Health { status: string; service: string; version: string; database: string; }
export interface Page<T> { items: T[]; total: number; limit: number; offset: number; }
export interface Student { id: string; name: string; program: string; email?: string; enrollment_year?: number; prev_gpa?: number; }
export interface Course { id: string; code: string; title: string; department: string; instructor_name: string; credits: number; term: string; difficulty: number; }
export interface Topic { id: string; course_id: string; name: string; sequence: number; difficulty: number; }

export interface DashboardOverview {
  totals: { students: number; courses: number; enrollments: number };
  avg_performance: number | null;
  attendance_avg: number | null;
  avg_course_health: number | null;
  feedback_sentiment: { n: number; positive: number; neutral: number; negative: number };
  performance_trend: { sequence: number; mean_pct: number }[];
  risk_distribution: Record<string, number> | null;
  recent_alerts: { severity: string; message: string; entity_id: string }[];
  ai_insights: string[];
}

export interface CourseHealth {
  course_id: string; course_title: string; score: number | null;
  components: Record<string, number | null>;
  weights: Record<string, number>;
  pass_rate: number | null;
  score_trend: { sequence: number; mean_pct: number }[];
  explanation: string;
}

export interface TopicPerf {
  topic_id: string; name: string; sequence: number; difficulty: number;
  mastery_pct: number | null; students: number; is_weak: boolean;
}

export interface RiskPrediction {
  student_id: string; risk_label: string; risk_probability: number;
  probabilities: Record<string, number>;
  features: Record<string, number | null>;
  explanation: string | null;
  shap_values: { base_value: number; top_factors: { feature: string; label: string; shap: number; value: number | null }[] } | null;
  predicted_at: string;
}

export interface Trajectory {
  student_id: string;
  score_series: { sequence: number; week: number; mean_pct: number; moving_avg: number }[];
  attendance_series: { week: number; rate: number }[];
  topic_mastery: { topic_id: string; mastery_pct: number }[];
  risk_trajectory: { sequence: number; week: number; risk_probability: number }[];
  summary: { score_slope: number | null; attendance_slope: number | null; volatility: number; trend: string; deteriorating: boolean; change_points: { at_sequence: number; drop: number }[] };
}

export interface Recommendation { type: string; reason: string; priority: number; target_topic?: string; }
export interface Recommendations { student_id: string; risk_label: string | null; risk_probability: number | null; recommendations: Recommendation[]; note: string; }

export interface FeedbackInsights {
  total: number;
  sentiment: Record<string, number>;
  sentiment_counts?: Record<string, number>;
  top_issues: { issue: string; count: number; share: number }[];
  topic_sentiment: { topic: string; total: number; positive: number; neutral: number; negative: number }[];
  sentiment_source?: string;
}

export interface AnalystAnswer {
  question: string; answer: string; mode: string; sufficient: boolean;
  citations: string[];
  evidence: { kind: string; statement: string; source: string; value: number | null }[];
  recommendations: string[];
  entities: Record<string, string>;
}

export interface DocumentMeta { id: number; title: string; doc_type: string; course_id: string | null; num_pages: number; num_chunks: number; status: string; embedding_method?: string; }
export interface RagResult { chunk_id: number; document_title: string; page: number; section: string | null; topic: string | null; content: string; similarity: number; score: number; citation: string; }
export interface RagResponse { query: string; results: RagResult[]; count: number; best_similarity: number; sufficient: boolean; embedding_method: string; }

export interface ModelVersion { id: number; name: string; version: string; model_type: string; status: string; created_at: string; metrics_summary: { f1_macro?: number; roc_auc_ovr_macro?: number; high_recall?: number; accuracy?: number }; metrics?: any; hyperparameters?: any; }
export interface Experiment { id: number; name: string; model_type: string; feature_set: string; created_at: string; metrics_summary: any; metrics?: any; }

export interface Intervention { id: number; student_id: string; type: string; reason: string; status: string; expected_outcome?: string; recommended_by: string; outcomes: { metric: string; before: number; after: number; delta: number }[]; }
export interface Effectiveness { n: number; mean_delta?: number; improved?: number; improved_share?: number | null; by_type?: Record<string, { n: number; mean_delta: number }>; caveat?: string; note?: string; }

// ---- endpoint helpers ----
const get = async <T>(url: string, params?: any): Promise<T> => (await api.get<T>(url, { params })).data;

export const getHealth = () => get<Health>("/api/health");
export const getDashboard = () => get<DashboardOverview>("/api/dashboard/overview");
export const listStudents = (params: { limit?: number; offset?: number; search?: string; program?: string }) => get<Page<Student>>("/api/students", params);
export const getStudent = (id: string) => get<Student>(`/api/students/${id}`);
export const getRisk = (id: string) => get<RiskPrediction>(`/api/students/${id}/risk`);
export const getTrajectory = (id: string) => get<Trajectory>(`/api/students/${id}/trajectory`);
export const getRecommendations = (id: string) => get<Recommendations>(`/api/students/${id}/recommendations`);
export const getAtRisk = (limit = 25) => get<{ student_id: string; name: string; program: string; risk_label: string; risk_probability: number }[]>("/api/students/at-risk", { limit });
export const listCourses = () => get<Course[]>("/api/courses");
export const getCourseHealth = (id: string) => get<CourseHealth>(`/api/courses/${id}/health`);
export const getCourseTopics = (id: string) => get<TopicPerf[]>(`/api/courses/${id}/topics/performance`);
export const getTopicPerf = (id: string) => get<any>(`/api/topics/${id}/performance`);
export const getTopicStudents = (id: string) => get<{ student_id: string; mastery_pct: number; assessments: number }[]>(`/api/topics/${id}/students`);
export const getWeakTopics = (limit = 10) => get<{ topic_id: string; name: string; course_id: string; mastery_pct: number }[]>("/api/topics/weak", { limit });
export const getFeedbackInsights = (course_id?: string) => get<FeedbackInsights>("/api/feedback/insights", course_id ? { course_id } : undefined);
export const getAnomalies = () => get<{ assessment: any[]; attendance: any[]; total: number }>("/api/analytics/anomalies");
export const getDataQuality = () => get<any>("/api/analytics/data-quality");
export const listModels = () => get<ModelVersion[]>("/api/models");
export const getModel = (id: number) => get<ModelVersion>(`/api/models/${id}`);
export const listExperiments = () => get<Experiment[]>("/api/experiments");
export const listDocuments = () => get<DocumentMeta[]>("/api/documents");
export const listInterventions = (student_id?: string) => get<Intervention[]>("/api/interventions", student_id ? { student_id } : undefined);
export const getEffectiveness = () => get<Effectiveness>("/api/interventions/effectiveness");

export const askAnalyst = async (question: string) => (await api.post<AnalystAnswer>("/api/analyst/query", { question })).data;
export const ragQuery = async (body: { query: string; course_id?: string; topic?: string; top_k?: number }) => (await api.post<RagResponse>("/api/rag/query", body)).data;
