from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_usersettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country", models.CharField(max_length=120)),
                ("role", models.CharField(choices=[("student", "Student"), ("teacher", "Teacher"), ("parent", "Parent"), ("school_admin", "School admin")], default="student", max_length=32)),
                ("age_range", models.CharField(choices=[("under_13", "Under 13"), ("13_15", "13-15"), ("16_18", "16-18"), ("19_24", "19-24"), ("25_34", "25-34"), ("35_plus", "35+"), ("prefer_not_to_say", "Prefer not to say")], default="prefer_not_to_say", max_length=32)),
                ("gender", models.CharField(choices=[("female", "Female"), ("male", "Male"), ("non_binary", "Non-binary"), ("prefer_to_self_describe", "Prefer to self describe"), ("prefer_not_to_say", "Prefer not to say")], default="prefer_not_to_say", max_length=32)),
                ("education_level", models.CharField(blank=True, choices=[("primary", "Primary school"), ("secondary", "Secondary school"), ("high_school", "High school"), ("undergraduate", "Undergraduate"), ("postgraduate", "Postgraduate"), ("teacher", "Teacher"), ("other", "Other"), ("prefer_not_to_say", "Prefer not to say")], max_length=32)),
                ("school_name", models.CharField(blank=True, max_length=255)),
                ("learning_goal", models.TextField(blank=True)),
                ("subjects_of_interest", models.JSONField(blank=True, default=list)),
                ("referral_source", models.CharField(blank=True, max_length=120)),
                ("preferred_language", models.CharField(blank=True, max_length=80)),
                ("timezone", models.CharField(blank=True, max_length=80)),
                ("device_type", models.CharField(blank=True, max_length=40)),
                ("browser", models.CharField(blank=True, max_length=80)),
                ("operating_system", models.CharField(blank=True, max_length=80)),
                ("signup_date", models.DateTimeField(auto_now_add=True)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                ("last_active_at", models.DateTimeField(blank=True, null=True)),
                ("login_count", models.PositiveIntegerField(default=0)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
