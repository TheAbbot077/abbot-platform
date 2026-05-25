from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import AgeRange, EducationLevel, GenderChoice, UserProfile, UserRole, UserSettings


class UserSettingsSerializer(serializers.ModelSerializer):
    theme_label = serializers.CharField(source="get_theme_display", read_only=True)

    class Meta:
        model = UserSettings
        fields = ["theme", "theme_label"]


class UserSerializer(serializers.ModelSerializer):
    settings = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email", "is_staff", "settings"]
        read_only_fields = fields

    def get_settings(self, user):
        settings, _created = UserSettings.objects.get_or_create(user=user)
        return UserSettingsSerializer(settings).data


class SignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    country = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=UserRole.choices)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    age_range = serializers.ChoiceField(choices=AgeRange.choices, required=False, default=AgeRange.PREFER_NOT_TO_SAY)
    gender = serializers.ChoiceField(choices=GenderChoice.choices, required=False, default=GenderChoice.PREFER_NOT_TO_SAY)
    education_level = serializers.ChoiceField(choices=EducationLevel.choices, required=False, allow_blank=True)
    school_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    learning_goal = serializers.CharField(required=False, allow_blank=True)
    subjects_of_interest = serializers.ListField(
        child=serializers.CharField(max_length=80),
        required=False,
        allow_empty=True,
    )
    referral_source = serializers.CharField(max_length=120, required=False, allow_blank=True)
    preferred_language = serializers.CharField(max_length=80, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if get_user_model().objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        username = attrs.get("username") or _username_from_email(attrs["email"])
        attrs["username"] = _unique_username(username)
        return attrs

    def validate_country(self, country: str) -> str:
        country = country.strip()
        if not country:
            raise serializers.ValidationError("Country is required for aggregate regional analytics.")
        return country

    def validate_subjects_of_interest(self, subjects: list[str]) -> list[str]:
        return [subject.strip() for subject in subjects if subject.strip()][:20]

    def validate_username(self, username: str) -> str:
        username = username.strip()
        if username and get_user_model().objects.filter(username=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return username

    def create(self, validated_data):
        profile_fields = {
            "country": validated_data.pop("country"),
            "role": validated_data.pop("role"),
            "age_range": validated_data.pop("age_range", AgeRange.PREFER_NOT_TO_SAY),
            "gender": validated_data.pop("gender", GenderChoice.PREFER_NOT_TO_SAY),
            "education_level": validated_data.pop("education_level", ""),
            "school_name": validated_data.pop("school_name", ""),
            "learning_goal": validated_data.pop("learning_goal", ""),
            "subjects_of_interest": validated_data.pop("subjects_of_interest", []),
            "referral_source": validated_data.pop("referral_source", ""),
            "preferred_language": validated_data.pop("preferred_language", ""),
            "timezone": validated_data.pop("timezone", ""),
        }
        validated_data.pop("confirm_password")
        user = get_user_model().objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        UserProfile.objects.create(user=user, **profile_fields)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_email = attrs["username"].strip()
        username = username_or_email

        if "@" in username_or_email:
            matching_user = get_user_model().objects.filter(email__iexact=username_or_email).first()
            if matching_user:
                username = matching_user.username

        # The frontend still sends the field as "username" for simplicity,
        # but students may naturally sign in with either username or email.
        user = authenticate(username=username, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Enter a valid username and password.")
        attrs["user"] = user
        return attrs


def _username_from_email(email: str) -> str:
    return email.split("@", 1)[0].strip() or "student"


def _unique_username(base_username: str) -> str:
    safe_base = "".join(character for character in base_username.lower() if character.isalnum() or character in "._-")
    safe_base = safe_base[:140] or "student"
    candidate = safe_base
    suffix = 1
    while get_user_model().objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{safe_base[:140]}-{suffix}"
    return candidate
