"use client";

import { FormEvent, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookOpen, GraduationCap, ShieldCheck, Sparkles } from "lucide-react";

import { login, signup } from "@/lib/api";
import type { SignupPayload } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [country, setCountry] = useState("");
  const [role, setRole] = useState<SignupPayload["role"]>("student");
  const [ageRange, setAgeRange] = useState<NonNullable<SignupPayload["age_range"]>>("prefer_not_to_say");
  const [gender, setGender] = useState<NonNullable<SignupPayload["gender"]>>("prefer_not_to_say");
  const [educationLevel, setEducationLevel] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [learningGoal, setLearningGoal] = useState("");
  const [subjectsOfInterest, setSubjectsOfInterest] = useState("");
  const [referralSource, setReferralSource] = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      if (mode === "signup") {
        await signup({
          first_name: firstName,
          last_name: lastName,
          email,
          password,
          confirm_password: confirmPassword,
          country,
          role,
          age_range: ageRange,
          gender,
          education_level: educationLevel,
          school_name: schoolName,
          learning_goal: learningGoal,
          subjects_of_interest: subjectsOfInterest.split(",").map((subject) => subject.trim()).filter(Boolean),
          referral_source: referralSource,
          preferred_language: preferredLanguage,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });
      } else {
        await login(identifier, password);
      }
      if (mode === "signup") {
        window.sessionStorage.setItem("signup_welcome", "true");
      }
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Authentication failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className={mode === "signup" ? "mx-auto w-full max-w-4xl overflow-hidden" : "mx-auto w-full max-w-md"}>
      <CardHeader className={mode === "signup" ? "border-b bg-muted/30" : ""}>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            {mode === "signup" ? <Sparkles className="h-5 w-5" aria-hidden="true" /> : <BookOpen className="h-5 w-5" aria-hidden="true" />}
          </div>
          <div>
            <CardTitle>{mode === "signup" ? "Create your study space" : "Welcome back"}</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              {mode === "signup"
                ? "This helps us personalize your learning experience."
                : "Log in and keep your learning journey moving."}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form className="space-y-5 pt-2" onSubmit={handleSubmit}>
          {mode === "signup" ? (
            <>
              <SectionCard
                icon={<ShieldCheck className="h-5 w-5" aria-hidden="true" />}
                title="Account details"
                description="The basics we need to create your secure account."
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <TextField label="First name" value={firstName} onChange={setFirstName} required />
                  <TextField label="Last name" value={lastName} onChange={setLastName} required />
                </div>
                <TextField label="Email" type="email" value={email} onChange={setEmail} required />
                <div className="grid gap-4 sm:grid-cols-2">
                  <TextField label="Password" type="password" value={password} onChange={setPassword} required />
                  <TextField label="Confirm password" type="password" value={confirmPassword} onChange={setConfirmPassword} required />
                </div>
              </SectionCard>

              <SectionCard
                icon={<GraduationCap className="h-5 w-5" aria-hidden="true" />}
                title="Learning profile"
                description="A quick snapshot so The Abbot can guide your next best step."
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <TextField label="Country" value={country} onChange={setCountry} required />
                  <SelectField label="User role" value={role} onChange={(value) => setRole(value as SignupPayload["role"])} required>
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                    <option value="parent">Parent</option>
                    <option value="school_admin">School admin</option>
                  </SelectField>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <SelectField label="Education level" optional value={educationLevel} onChange={setEducationLevel}>
                    <option value="">Skip for now</option>
                    <option value="primary">Primary school</option>
                    <option value="secondary">Secondary school</option>
                    <option value="high_school">High school</option>
                    <option value="undergraduate">Undergraduate</option>
                    <option value="postgraduate">Postgraduate</option>
                    <option value="teacher">Teacher</option>
                    <option value="other">Other</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </SelectField>
                  <TextField label="Preferred language" optional value={preferredLanguage} onChange={setPreferredLanguage} placeholder="English" />
                </div>
                <TextField label="Subjects of interest" optional value={subjectsOfInterest} onChange={setSubjectsOfInterest} placeholder="Math, Economics, Biology" helper="Separate subjects with commas." />
                <TextField label="Learning goal" optional value={learningGoal} onChange={setLearningGoal} placeholder="Pass exams, understand algebra, prep for class..." />
              </SectionCard>

              <SectionCard
                icon={<Sparkles className="h-5 w-5" aria-hidden="true" />}
                title="Optional demographics"
                description="Helpful for aggregate insights. You can choose prefer not to say."
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <SelectField label="Age range" optional value={ageRange} onChange={(value) => setAgeRange(value as NonNullable<SignupPayload["age_range"]>)}>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                    <option value="under_13">Under 13</option>
                    <option value="13_15">13-15</option>
                    <option value="16_18">16-18</option>
                    <option value="19_24">19-24</option>
                    <option value="25_34">25-34</option>
                    <option value="35_plus">35+</option>
                  </SelectField>
                  <SelectField label="Gender" optional value={gender} onChange={(value) => setGender(value as NonNullable<SignupPayload["gender"]>)}>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="non_binary">Non-binary</option>
                    <option value="prefer_to_self_describe">Prefer to self describe</option>
                  </SelectField>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <TextField label="School name" optional value={schoolName} onChange={setSchoolName} />
                  <TextField label="How did you hear about us?" optional value={referralSource} onChange={setReferralSource} placeholder="Friend, teacher, search..." />
                </div>
              </SectionCard>
            </>
          ) : (
            <TextField label="Username or email" value={identifier} onChange={setIdentifier} required />
          )}
          {mode === "login" ? (
            <TextField label="Password" type="password" value={password} onChange={setPassword} required />
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button className={mode === "signup" ? "min-h-11 w-full text-base sm:w-auto sm:px-8" : "w-full"} type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Working..." : mode === "signup" ? "Start studying" : "Log in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          {mode === "signup" ? "Already have an account? " : "New here? "}
          <Link className="font-medium text-primary" href={mode === "signup" ? "/login" : "/signup"}>
            {mode === "signup" ? "Log in" : "Create an account"}
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}

function SectionCard({
  icon,
  title,
  description,
  children,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border bg-background p-4 shadow-sm sm:p-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder,
  optional = false,
  helper,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
  optional?: boolean;
  helper?: string;
}) {
  return (
    <label className="block text-sm font-medium">
      <span className="flex items-center justify-between gap-3">
        <span>{label}</span>
        {optional ? <span className="text-xs font-normal text-muted-foreground">Optional</span> : null}
      </span>
      <input
        className="mt-2 min-h-10 w-full rounded-md border bg-background px-3 text-sm"
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        placeholder={placeholder}
      />
      {helper ? <span className="mt-1 block text-xs font-normal text-muted-foreground">{helper}</span> : null}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  children,
  required = false,
  optional = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  required?: boolean;
  optional?: boolean;
}) {
  return (
    <label className="block text-sm font-medium">
      <span className="flex items-center justify-between gap-3">
        <span>{label}</span>
        {optional ? <span className="text-xs font-normal text-muted-foreground">Optional</span> : null}
      </span>
      <select
        className="mt-2 min-h-10 w-full rounded-md border bg-background px-3 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
      >
        {children}
      </select>
    </label>
  );
}
