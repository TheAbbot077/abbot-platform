from rest_framework import serializers


class CommandCenterMetricSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()


class CommandCenterRecentDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    owner_username = serializers.CharField()
    subject_name = serializers.CharField(allow_blank=True, allow_null=True)
    status = serializers.CharField()
    parser_confidence_score = serializers.FloatField(allow_null=True)
    parser_strategy = serializers.CharField(allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CommandCenterFailedJobSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    title = serializers.CharField()
    owner_username = serializers.CharField()
    status = serializers.CharField()
    parser_warnings = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    updated_at = serializers.DateTimeField()


class CommandCenterDashboardSerializer(serializers.Serializer):
    title = serializers.CharField()
    metrics = CommandCenterMetricSerializer(many=True)
    recent_uploaded_textbooks = CommandCenterRecentDocumentSerializer(many=True)
    recent_failed_jobs = CommandCenterFailedJobSerializer(many=True)


class AdminAnalyticsBucketSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.IntegerField()


class AdminSignupTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    signups = serializers.IntegerField()


class AdminTextbookUploadTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    uploads = serializers.IntegerField()


class AdminConceptCompletionTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    completions = serializers.IntegerField()


class AdminQuizTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    passed = serializers.IntegerField()
    failed = serializers.IntegerField()
    total = serializers.IntegerField()


class AdminUserAnalyticsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    currently_active_users = serializers.IntegerField()
    users_logged_in_today = serializers.IntegerField()
    daily_active_users = serializers.IntegerField()
    weekly_active_users = serializers.IntegerField()
    monthly_active_users = serializers.IntegerField()
    users_by_country = AdminAnalyticsBucketSerializer(many=True)
    users_by_age_range = AdminAnalyticsBucketSerializer(many=True)
    users_by_gender = AdminAnalyticsBucketSerializer(many=True)
    users_by_education_level = AdminAnalyticsBucketSerializer(many=True)
    users_by_role = AdminAnalyticsBucketSerializer(many=True)
    new_signups_over_time = AdminSignupTrendSerializer(many=True)
    textbook_uploads_over_time = AdminTextbookUploadTrendSerializer(many=True)
    concept_completions_over_time = AdminConceptCompletionTrendSerializer(many=True)
    quiz_pass_fail_trends = AdminQuizTrendSerializer(many=True)
    most_active_subjects = AdminAnalyticsBucketSerializer(many=True)
    average_textbooks_per_user = serializers.FloatField()
    average_concepts_completed_per_user = serializers.FloatField()
    privacy_note = serializers.CharField()


class AdminUserListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    is_active = serializers.BooleanField()
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    last_login = serializers.DateTimeField(allow_null=True)
    subject_count = serializers.IntegerField()
    document_count = serializers.IntegerField()
    quiz_attempt_count = serializers.IntegerField()


class AdminUserListSerializer(serializers.Serializer):
    users = AdminUserListItemSerializer(many=True)
    total_count = serializers.IntegerField()


class AdminUserSubjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    document_count = serializers.IntegerField()


class AdminUserDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    subject_name = serializers.CharField(allow_blank=True, allow_null=True)
    status = serializers.CharField()
    parser_confidence_score = serializers.FloatField(allow_null=True)
    created_at = serializers.DateTimeField()


class AdminUserProgressSerializer(serializers.Serializer):
    total_progress_records = serializers.IntegerField()
    locked = serializers.IntegerField()
    available = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    passed = serializers.IntegerField()
    failed = serializers.IntegerField()
    quiz_attempts = serializers.IntegerField()
    tutor_sessions = serializers.IntegerField()


class AdminUserDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    is_active = serializers.BooleanField()
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    last_login = serializers.DateTimeField(allow_null=True)
    summary = serializers.DictField()
    subjects = AdminUserSubjectSerializer(many=True)
    textbooks = AdminUserDocumentSerializer(many=True)
    learning_progress = AdminUserProgressSerializer()


class AdminChapterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    sequence_number = serializers.IntegerField()
    concept_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class AdminTextbookSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    owner_username = serializers.CharField()
    subject_name = serializers.CharField(allow_blank=True, allow_null=True)
    status = serializers.CharField()
    parser_confidence_score = serializers.FloatField(allow_null=True)
    parser_strategy = serializers.CharField(allow_blank=True, allow_null=True)
    parser_warnings = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    chapter_count = serializers.IntegerField()
    concept_count = serializers.IntegerField()
    progress_exists = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminTextbookListSerializer(serializers.Serializer):
    textbooks = AdminTextbookSerializer(many=True)
    total_count = serializers.IntegerField()


class AdminTextbookDetailSerializer(AdminTextbookSerializer):
    chapters = AdminChapterSerializer(many=True)
    progress_summary = serializers.DictField(child=serializers.IntegerField())


class AdminParserChapterProposalSerializer(serializers.Serializer):
    sequence_number = serializers.IntegerField()
    title = serializers.CharField()
    confidence_score = serializers.FloatField(allow_null=True)
    detection_methods = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    preview = serializers.CharField()


class AdminParserPreviewSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    title = serializers.CharField()
    current_stored_chapters = AdminChapterSerializer(many=True)
    legacy = serializers.DictField()
    resolver = serializers.DictField()
    differences = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    progress_summary = serializers.DictField(child=serializers.IntegerField())
    progress_exists = serializers.BooleanField()


class AdminConceptQualitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    sequence_number = serializers.IntegerField()
    chapter_id = serializers.IntegerField()
    chapter_title = serializers.CharField()
    chapter_sequence_number = serializers.IntegerField()
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    owner_username = serializers.CharField()
    question_count = serializers.IntegerField()
    unanswered_question_count = serializers.IntegerField()
    quiz_attempt_count = serializers.IntegerField()
    pass_count = serializers.IntegerField()
    fail_count = serializers.IntegerField()
    pass_rate = serializers.FloatField(allow_null=True)
    lesson_count = serializers.IntegerField()
    tutor_message_count = serializers.IntegerField()
    possible_objective_match = serializers.BooleanField()
    matched_objective = serializers.CharField(allow_blank=True, allow_null=True)


class AdminCommonlyFailedConceptSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    chapter_title = serializers.CharField()
    document_title = serializers.CharField()
    fail_count = serializers.IntegerField()
    pass_rate = serializers.FloatField(allow_null=True)


class AdminFlaggedQuestionsSummarySerializer(serializers.Serializer):
    flagging_available = serializers.BooleanField()
    total_count = serializers.IntegerField()
    questions = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    message = serializers.CharField()


class AdminConceptQualityListSerializer(serializers.Serializer):
    concepts = AdminConceptQualitySerializer(many=True)
    total_count = serializers.IntegerField()
    commonly_failed_concepts = AdminCommonlyFailedConceptSerializer(many=True)
    flagged_questions = AdminFlaggedQuestionsSummarySerializer()


class AdminAuditLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    admin_user_id = serializers.IntegerField(allow_null=True)
    admin_username = serializers.CharField(allow_blank=True, allow_null=True)
    action = serializers.CharField()
    target_type = serializers.CharField()
    target_id = serializers.CharField(allow_blank=True)
    description = serializers.CharField()
    metadata = serializers.DictField()
    ip_address = serializers.IPAddressField(allow_null=True)
    created_at = serializers.DateTimeField()


class AdminAuditLogListSerializer(serializers.Serializer):
    logs = AdminAuditLogSerializer(many=True)
    total_count = serializers.IntegerField()
