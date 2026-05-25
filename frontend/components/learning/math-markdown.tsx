"use client";

import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";

import { normalizeTutorMath } from "@/lib/math-normalizer";
import { cn } from "@/lib/utils";

type MathMarkdownProps = {
  children: string;
  className?: string;
  muted?: boolean;
};

export function MathMarkdown({ children, className, muted = false }: MathMarkdownProps) {
  return (
    <div className={cn("math-markdown text-sm leading-6", muted ? "text-muted-foreground" : "text-foreground", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          code: ({ children }) => <code className="rounded bg-muted px-1 py-0.5 text-[0.9em] break-words">{children}</code>
        }}
      >
        {normalizeTutorMath(children)}
      </ReactMarkdown>
    </div>
  );
}
