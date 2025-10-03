"use client"

import { Button } from "@/components/ui/button";
import { Github, Loader2 } from "lucide-react";
import React from "react";
import { twMerge } from "tailwind-merge";

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
      variant="outline"
      className={ twMerge(`w-full inline-flex items-center justify-center gap-3 px-4 py-3 rounded cursor-pointer`, className)}
    >
      {loading ? <Loader2 className="animate-spin" /> : <Github />}
      <span>Continue With Github</span>
    </Button>
  );
}