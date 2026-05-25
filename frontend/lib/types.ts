export type ConceptStatus = "locked" | "available" | "in_progress" | "passed" | "failed";
export type BloomLevel = "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
export type ThemeKey =
  | "black_white_gold"
  | "royal_blue_white_gold"
  | "green_white_gold"
  | "red_white_gold"
  | "purple_white_gold";
export type CelebrationType = "concept_passed" | "chapter_completed" | "document_completed" | "ariel_examiner_passed";

export type DashboardConcept = {
  concept_id: number;
  title: string;
  sequence_number: number;
  is_required: boolean;
  status: ConceptStatus;
  last_score: string | null;
  bloom_level_scores?: Partial<Record<BloomLevel, string>>;
  mastery_score?: string | null;
  decayed_mastery_score?: string | null;
  mastery_strength?: "fast" | "medium" | "slow" | null;
  last_reviewed_at?: string | null;
  next_review_at?: string | null;
  forgetting_rate?: string | null;
  ariel_teachable?: boolean;
  ariel_taught?: boolean;
};

export type ChapterConcept = {
  id: number;
  title: string;
  sequence_number: number;
  is_required: boolean;
  summary: string;
  created_at: string;
  updated_at: string;
};

export type DashboardChapter = {
  chapter_id: number;
  title: string;
  sequence_number: number;
  completion_percentage: string;
  ariel_teachable_count?: number;
  ariel_examiner_unlocked?: boolean;
  concepts: DashboardConcept[];
};

export type DashboardDocument = {
  document_id: number;
  subject_id: number | null;
  subject_name: string | null;
  title: string;
  status: string;
  completion_percentage: string;
  current_recommended_next_action: string;
  current_chapter_title?: string | null;
  current_concept_title?: string | null;
  chapters: DashboardChapter[];
};

export type DashboardResponse = {
  documents: DashboardDocument[];
  student_ai_reinforcement?: {
    headline: string;
    recommendations: ReinforcementRecommendation[];
  };
  teachback_memory_engine?: TeachBackMemoryEngine;
};

export type User = {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  settings?: UserSettings;
};

export type AuthResponse = {
  user: User;
};

export type SignupPayload = {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
  country: string;
  role: "student" | "teacher" | "parent" | "school_admin";
  age_range?: "under_13" | "13_15" | "16_18" | "19_24" | "25_34" | "35_plus" | "prefer_not_to_say";
  gender?: "female" | "male" | "non_binary" | "prefer_to_self_describe" | "prefer_not_to_say";
  education_level?: string;
  school_name?: string;
  learning_goal?: string;
  subjects_of_interest?: string[];
  referral_source?: string;
  preferred_language?: string;
  timezone?: string;
};

export type UserSettings = {
  theme: ThemeKey;
  theme_label: string;
};

export type Subject = {
  id: number;
  name: string;
  document_count: number;
  created_at: string;
  updated_at: string;
};

export type DocumentUploadResponse = {
  id: number;
  subject: number | null;
  subject_name: string | null;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ReinforcementRecommendation = {
  id: number;
  concept_id: number;
  concept_title: string;
  chapter_id: number;
  chapter_title: string;
  document_id: number;
  document_title: string;
  reason: string;
  friendly_label?: string;
  friendly_message?: string;
  mission_title?: string;
  failed_bloom_level: BloomLevel;
  student_ai_score: string;
  recommended_action: string;
  priority: "low" | "medium" | "high";
  created_at: string;
};

export type TeachBackMemoryEngine = {
  feature_name: string;
  headline: string;
  memory_health: {
    score: string;
    label: string;
  };
  rusty_alerts: ReinforcementRecommendation[];
  daily_rescue_missions: ReinforcementRecommendation[];
  concept_strength_badges: Array<{
    concept_id: number;
    concept_title: string;
    label: string;
    score: string;
  }>;
  reinforcement_streak: {
    count: number;
    label: string;
  };
  teach_back_challenge: {
    title: string;
    prompt: string;
  };
  bloom_mastery_badges: Array<{
    bloom_level: BloomLevel;
    label: string;
    status: string;
  }>;
};

export type CurrentConcept = {
  concept_id: number;
  chapter_id: number;
  subject_id: number | null;
  subject_name: string | null;
  chapter_title?: string;
  chapter_sequence_number: number;
  title: string;
  sequence_number: number;
  is_required: boolean;
  status: ConceptStatus;
  attempts_count?: number;
  last_score: string | null;
  unlocked_at?: string | null;
  mastered_at?: string | null;
};

export type CurrentConceptResponse = {
  current_concept: CurrentConcept | null;
};

export type TutorLesson = {
  concept_id: number;
  concept_name: string;
  explanation: string;
  examples: string[];
  visual_content?: VisualContent | null;
  is_literary?: boolean;
  literary_metadata?: LiteraryMetadata;
  next_action: string;
};

export type LiteraryMetadata = {
  summary?: string;
  key_events?: string[];
  characters_present?: string[];
  character_development?: string[];
  themes?: string[];
  symbols?: string[];
  literary_devices?: string[];
  important_quotes?: string[];
  interpretation_questions?: string[];
};

export type TutorLessonResponse = TutorLesson | {
  lesson: null;
  next_action: string;
};

export type TutorAnswer = {
  concept_id: number;
  student_question: string;
  tutor_answer: string;
  visual_content?: VisualContent | null;
  source_mode: "document_only" | "document_plus_general_knowledge" | "general_knowledge_clarification";
  next_action: "continue_studying" | "ready_for_mcq";
};

export type VisualContent = {
  type: "graph" | "chart" | "table" | "geometry";
  title: string;
  description: string;
  expression: string;
  render_mode: "function_plot" | "coordinate_plane" | "geometry_diagram" | "curve_diagram" | "statistics_chart" | "conceptual_diagram";
  shape?: GeometryShape;
  labels?: string[];
  annotations?: GeometryAnnotation[];
  chart_type?: ChartType;
  x_label?: string;
  y_label?: string;
  data?: ChartDataPoint[];
};

export type GeometryShape =
  | "circle"
  | "triangle"
  | "rectangle"
  | "square"
  | "coordinate_point"
  | "line_segment"
  | "angle"
  | "polygon";

export type GeometryAnnotation = {
  label: string;
  position: string;
};

export type ChartType = "bar" | "line" | "pie" | "table";

export type ChartDataPoint = {
  label: string;
  value: number;
};

export type QuizOptionKey = "A" | "B" | "C" | "D";

export type QuizQuestion = {
  id: number;
  concept_id: number;
  question_type: "multiple_choice" | "short_answer";
  question_text: string;
  options: Partial<Record<QuizOptionKey, string>>;
  evidence_guidance: string;
  is_answered: boolean;
  bloom_level: BloomLevel;
};

export type MCQResponse = {
  questions: QuizQuestion[];
};

export type QuizAnswers = Record<string, string>;

export type QuizSubmissionResult = {
  attempt_id: number;
  concept_id: number;
  score: string;
  bloom_level_scores: Partial<Record<BloomLevel, string>>;
  passed: boolean;
  total_questions: number;
  correct_answers: number;
  remediation: string;
  remediation_message?: string;
  available_actions?: Array<"ask_tutor" | "restart_concept" | "retry_quiz">;
  next_action: string;
  celebration: CelebrationType | null;
};

export type ArielExaminerResult = {
  attempt_id: number;
  concept_id: number;
  question: string;
  student_ai_answer: string;
  score: string;
  passed: boolean;
  feedback: string;
  retention_score_at_quiz: string;
  celebration: CelebrationType | null;
};

export type ArielMemory = {
  concept_id: number;
  taught_content: string;
  taught_at: string;
  initial_mastery_score: string;
  current_retention_score: string;
  retention_strength: string;
  last_spot_quiz_at: string | null;
  next_review_at: string | null;
};

export type CommandCenterMetric = {
  key: string;
  label: string;
  value: number;
};

export type CommandCenterRecentDocument = {
  id: number;
  title: string;
  owner_username: string;
  subject_name: string | null;
  status: string;
  parser_confidence_score: number | null;
  parser_strategy: string | null;
  created_at: string;
  updated_at: string;
};

export type CommandCenterFailedJob = {
  document_id: number;
  title: string;
  owner_username: string;
  status: string;
  parser_warnings: string[];
  updated_at: string;
};

export type CommandCenterDashboard = {
  title: string;
  metrics: CommandCenterMetric[];
  recent_uploaded_textbooks: CommandCenterRecentDocument[];
  recent_failed_jobs: CommandCenterFailedJob[];
};

export type AdminAnalyticsBucket = {
  label: string;
  value: number;
};

export type AdminSignupTrend = {
  date: string;
  signups: number;
};

export type AdminTextbookUploadTrend = {
  date: string;
  uploads: number;
};

export type AdminConceptCompletionTrend = {
  date: string;
  completions: number;
};

export type AdminQuizTrend = {
  date: string;
  passed: number;
  failed: number;
  total: number;
};

export type AdminUserAnalytics = {
  total_users: number;
  currently_active_users: number;
  users_logged_in_today: number;
  daily_active_users: number;
  weekly_active_users: number;
  monthly_active_users: number;
  users_by_country: AdminAnalyticsBucket[];
  users_by_age_range: AdminAnalyticsBucket[];
  users_by_gender: AdminAnalyticsBucket[];
  users_by_education_level: AdminAnalyticsBucket[];
  users_by_role: AdminAnalyticsBucket[];
  new_signups_over_time: AdminSignupTrend[];
  textbook_uploads_over_time: AdminTextbookUploadTrend[];
  concept_completions_over_time: AdminConceptCompletionTrend[];
  quiz_pass_fail_trends: AdminQuizTrend[];
  most_active_subjects: AdminAnalyticsBucket[];
  average_textbooks_per_user: number;
  average_concepts_completed_per_user: number;
  privacy_note: string;
};

export type AdminUserListItem = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
  subject_count: number;
  document_count: number;
  quiz_attempt_count: number;
};

export type AdminUserListResponse = {
  users: AdminUserListItem[];
  total_count: number;
};

export type AdminUserDetail = AdminUserListItem & {
  summary: {
    subject_count: number;
    document_count: number;
    ready_document_count: number;
    failed_document_count: number;
    quiz_attempt_count: number;
    tutor_session_count: number;
  };
  subjects: Array<{
    id: number;
    name: string;
    document_count: number;
  }>;
  textbooks: Array<{
    id: number;
    title: string;
    subject_name: string | null;
    status: string;
    parser_confidence_score: number | null;
    created_at: string;
  }>;
  learning_progress: {
    total_progress_records: number;
    locked: number;
    available: number;
    in_progress: number;
    passed: number;
    failed: number;
    quiz_attempts: number;
    tutor_sessions: number;
  };
};

export type AdminChapter = {
  id: number;
  title: string;
  sequence_number: number;
  concept_count: number;
  created_at: string;
};

export type AdminTextbook = {
  id: number;
  title: string;
  owner_username: string;
  subject_name: string | null;
  status: string;
  parser_confidence_score: number | null;
  parser_strategy: string | null;
  parser_warnings: string[];
  chapter_count: number;
  concept_count: number;
  progress_exists: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminTextbookListResponse = {
  textbooks: AdminTextbook[];
  total_count: number;
};

export type AdminTextbookDetail = AdminTextbook & {
  chapters: AdminChapter[];
  progress_summary: Record<string, number>;
};

export type AdminParserPreviewChapter = {
  sequence_number: number;
  title: string;
  confidence_score: number | null;
  detection_methods: string[];
  preview: string;
};

export type AdminParserPreview = {
  document_id: number;
  title: string;
  current_stored_chapters: AdminChapter[];
  legacy: {
    strategy_used: string;
    confidence_score: number;
    warnings: string[];
    accepted_chapter_count: number;
    accepted_chapters: AdminParserPreviewChapter[];
  };
  resolver: {
    strategy_used: string;
    confidence_score: number;
    warnings: string[];
    accepted_chapter_count: number;
    accepted_chapters: AdminParserPreviewChapter[];
  };
  differences: string[];
  progress_summary: Record<string, number>;
  progress_exists: boolean;
};

export type AdminConceptQuality = {
  id: number;
  title: string;
  sequence_number: number;
  chapter_id: number;
  chapter_title: string;
  chapter_sequence_number: number;
  document_id: number;
  document_title: string;
  owner_username: string;
  question_count: number;
  unanswered_question_count: number;
  quiz_attempt_count: number;
  pass_count: number;
  fail_count: number;
  pass_rate: number | null;
  lesson_count: number;
  tutor_message_count: number;
  possible_objective_match: boolean;
  matched_objective: string | null;
};

export type AdminCommonlyFailedConcept = {
  id: number;
  title: string;
  chapter_title: string;
  document_title: string;
  fail_count: number;
  pass_rate: number | null;
};

export type AdminConceptQualityResponse = {
  concepts: AdminConceptQuality[];
  total_count: number;
  commonly_failed_concepts: AdminCommonlyFailedConcept[];
  flagged_questions: {
    flagging_available: boolean;
    total_count: number;
    questions: Array<Record<string, unknown>>;
    message: string;
  };
};

export type AdminRegenerationResponse = {
  detail: string;
  concept_id: number;
  deleted_count: number;
  tutor_messages_preserved?: number;
};

export type AdminAuditLog = {
  id: number;
  admin_user_id: number | null;
  admin_username: string | null;
  action: string;
  target_type: string;
  target_id: string;
  description: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
};

export type AdminAuditLogResponse = {
  logs: AdminAuditLog[];
  total_count: number;
};
