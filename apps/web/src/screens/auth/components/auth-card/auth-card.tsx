"use client"
import React, { useState } from "react";
import { GithubButton } from "../github-button";
import Logo from "@/components/brand/logo";

export default function AuthCard() {
  const [loading, setLoading] = useState(false);

  function startGithubLogin() {
    setLoading(true);
    // Backend will handle:
    // 1) redirect to GitHub authorize URL
    // 2) exchange code -> temporary access token
    // 3) exchange temporary token -> id_token, set cookie, then redirect back
    const redirect = typeof window !== "undefined" ? window.location.href : "/";
    window.location.href = `/api/auth/github/start?redirect=${encodeURIComponent(redirect)}`;
  }

  return (
		<div className="lg:w-1/2 flex flex-col mx-auto px-6 py-3 min-h-screen font-secondary">
      <Logo/>
			<div className=" flex-1 w-full flex justify-center items-center max-w-[640px]">

        <div>
          <p className="font-secondary tracking-wide text-4xl font-medium">
						Welcome Back
					</p>
					<p className="font-secondary tracking-wide font-medium text-muted-foreground text-xs">
						{"Let's"} get you logged back in, We need a few more
						credentials!
					</p>

          <GithubButton onClick={startGithubLogin} loading={loading} className="mt-6 w-full flex items-center justify-center" />

          <p className="text-xs text-muted-foreground mt-2">
            By continuing you agree to the terms.
          </p>
        </div>
      </div>
    </div>
  );
}