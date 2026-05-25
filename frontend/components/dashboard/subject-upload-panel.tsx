"use client";

import { FormEvent, useState } from "react";
import { Plus, Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createSubject, deleteSubject, uploadDocument } from "@/lib/api";
import type { Subject } from "@/lib/types";

export function SubjectUploadPanel({
  subjects,
  onChanged,
  fixedSubjectId
}: {
  subjects: Subject[];
  onChanged: () => void;
  fixedSubjectId?: number;
}) {
  const [subjectName, setSubjectName] = useState("");
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(fixedSubjectId ?? subjects[0]?.id ?? null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleCreateSubject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage(null);
    try {
      const subject = await createSubject(subjectName.trim());
      setSubjectName("");
      setSelectedSubjectId(subject.id);
      setMessage("Nice. Your new subject is ready for a textbook.");
      onChanged();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not create subject.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setMessage("Choose a PDF first.");
      return;
    }

    setIsSubmitting(true);
    setMessage(null);
    try {
      await uploadDocument(title || file.name.replace(/\.pdf$/i, ""), fixedSubjectId ?? selectedSubjectId, file);
      setTitle("");
      setFile(null);
      setMessage("Upload started. We are preparing your textbook now.");
      onChanged();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not upload this PDF.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteSubject(subject: Subject) {
    const confirmed = window.confirm(`Delete subject "${subject.name}"? This only works after its textbooks have been deleted.`);
    if (!confirmed) {
      return;
    }

    setIsSubmitting(true);
    setMessage(null);
    try {
      await deleteSubject(subject.id);
      if (selectedSubjectId === subject.id) {
        setSelectedSubjectId(null);
      }
      setMessage("Subject deleted.");
      onChanged();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Could not delete this subject.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="overflow-hidden bg-card/95 shadow-sm">
      <CardHeader>
        <CardTitle>Add something to study</CardTitle>
      </CardHeader>
      <CardContent className={`grid gap-5 ${fixedSubjectId ? "" : "lg:grid-cols-2"}`}>
        {!fixedSubjectId ? (
        <form className="space-y-3 rounded-2xl bg-muted/60 p-4" onSubmit={handleCreateSubject}>
          <label className="block text-sm font-medium">
            New subject
            <input className="mt-2 min-h-11 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" value={subjectName} onChange={(event) => setSubjectName(event.target.value)} placeholder="Economics" />
          </label>
          <Button type="submit" variant="outline" className="w-full sm:w-auto" disabled={isSubmitting || !subjectName.trim()}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add subject
          </Button>
          {subjects.length > 0 ? (
            <div className="space-y-2 border-t pt-3">
              <p className="text-xs font-medium text-muted-foreground">Your subjects</p>
              {subjects.map((subject) => (
                <div key={subject.id} className="flex flex-col gap-3 rounded-2xl border bg-background p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                  <span className="break-words">{subject.name} ({subject.document_count} books)</span>
                  <Button type="button" variant="outline" size="sm" className="w-full sm:w-auto" onClick={() => handleDeleteSubject(subject)} disabled={isSubmitting}>
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          ) : null}
        </form>
        ) : null}

        <form className="space-y-3 rounded-2xl bg-muted/60 p-4" onSubmit={handleUpload}>
          {!fixedSubjectId ? (
          <label className="block text-sm font-medium">
            Put it under
            <select className="mt-2 min-h-11 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" value={selectedSubjectId ?? ""} onChange={(event) => setSelectedSubjectId(event.target.value ? Number(event.target.value) : null)}>
              <option value="">No subject</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>{subject.name}</option>
              ))}
            </select>
          </label>
          ) : null}
          <label className="block text-sm font-medium">
            Textbook nickname
            <input className="mt-2 min-h-11 w-full rounded-xl border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Introductory Economics" />
          </label>
          <label className="block text-sm font-medium">
            Choose PDF
            <input className="mt-2 block w-full rounded-xl border bg-background px-3 py-3 text-sm file:mr-3 file:rounded-full file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-sm file:font-medium file:text-secondary-foreground" type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <Button type="submit" className="w-full sm:w-auto" disabled={isSubmitting || !file}>
            <Upload className="h-4 w-4" aria-hidden="true" />
            Add textbook
          </Button>
        </form>
        {message ? <p className="lg:col-span-2 text-sm text-muted-foreground">{message}</p> : null}
      </CardContent>
    </Card>
  );
}
