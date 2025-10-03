"use client"

import { Button } from "@/components/ui/button";
import { Github, Loader2 } from "lucide-react";
import React from "react";

type Props = {
  onClick: () => void;
  loading?: boolean;
  ariaLabel?: string;
  className?: string;
};

export default function GithubButton({
  onClick,
  loading = false,
  ariaLabel = "Continue with GitHub",
  className = "",
}: Props) {
  return (
    <Button
      onClick={onClick}
      disabled={loading}
      aria-label={ariaLabel}
      className={`w-full inline-flex items-center justify-center gap-3 px-4 py-3 rounded shadow hover:opacity-95 disabled:opacity-60 bg-primary text-primary-foreground ${className}`}
    >
      {loading ? <Loader2 className="animate-spin" /> : <Github />}
      <span>{loading ? "Redirecting..." : "Continue With Github"}</span>
    </Button>
  );
}