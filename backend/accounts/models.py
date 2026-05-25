from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class User(AbstractUser):
    """Application user.

    A custom user model from the beginning keeps future SaaS requirements
    flexible without requiring a risky auth migration later.
    """

    pass


class UserRole(models.TextChoices):
    STUDENT = "student", "Student"
    TEACHER = "teacher", "Teacher"
    PARENT = "parent", "Parent"
    SCHOOL_ADMIN = "school_admin", "School admin"


class AgeRange(models.TextChoices):
    UNDER_13 = "under_13", "Under 13"
    AGE_13_15 = "13_15", "13-15"
    AGE_16_18 = "16_18", "16-18"
    AGE_19_24 = "19_24", "19-24"
    AGE_25_34 = "25_34", "25-34"
    AGE_35_PLUS = "35_plus", "35+"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class GenderChoice(models.TextChoices):
    FEMALE = "female", "Female"
    MALE = "male", "Male"
    NON_BINARY = "non_binary", "Non-binary"
    SELF_DESCRIBE = "prefer_to_self_describe", "Prefer to self describe"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class EducationLevel(models.TextChoices):
    PRIMARY = "primary", "Primary school"
    SECONDARY = "secondary", "Secondary school"
    HIGH_SCHOOL = "high_school", "High school"
    UNDERGRADUATE = "undergraduate", "Undergraduate"
    POSTGRADUATE = "postgraduate", "Postgraduate"
    TEACHER = "teacher", "Teacher"
    OTHER = "other", "Other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"


class UserProfile(models.Model):
    """Privacy-conscious profile and analytics fields.

    Demographic fields are intentionally separate from auth credentials and are
    mostly optional. Admin analytics should aggregate these values by default,
    not expose sensitive profile details for individual students.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    country = models.CharField(max_length=120)
    role = models.CharField(max_length=32, choices=UserRole.choices, default=UserRole.STUDENT)
    age_range = models.CharField(max_length=32, choices=AgeRange.choices, default=AgeRange.PREFER_NOT_TO_SAY)
    gender = models.CharField(max_length=32, choices=GenderChoice.choices, default=GenderChoice.PREFER_NOT_TO_SAY)
    education_level = models.CharField(max_length=32, choices=EducationLevel.choices, blank=True)
    school_name = models.CharField(max_length=255, blank=True)
    learning_goal = models.TextField(blank=True)
    subjects_of_interest = models.JSONField(default=list, blank=True)
    referral_source = models.CharField(max_length=120, blank=True)
    preferred_language = models.CharField(max_length=80, blank=True)
    timezone = models.CharField(max_length=80, blank=True)
    device_type = models.CharField(max_length=40, blank=True)
    browser = models.CharField(max_length=80, blank=True)
    operating_system = models.CharField(max_length=80, blank=True)
    signup_date = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.user} profile"


class ThemeChoice(models.TextChoices):
    BLACK_WHITE_GOLD = "black_white_gold", "Black, white and gold"
    ROYAL_BLUE_WHITE_GOLD = "royal_blue_white_gold", "Royal blue, white and gold"
    GREEN_WHITE_GOLD = "green_white_gold", "Green, white and gold"
    RED_WHITE_GOLD = "red_white_gold", "Red, white and gold"
    PURPLE_WHITE_GOLD = "purple_white_gold", "Purple, white and gold"


class UserSettings(models.Model):
    """Per-user product preferences.

    Theme is stored as a stable key so the frontend can map it to CSS variables
    without hardcoding colors across individual components.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settings")
    theme = models.CharField(
        max_length=32,
        choices=ThemeChoice.choices,
        default=ThemeChoice.BLACK_WHITE_GOLD,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "user settings"
        verbose_name_plural = "user settings"

    def __str__(self) -> str:
        return f"{self.user} settings"
