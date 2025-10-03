"use client"

import { useState } from "react";

export default function Signin() {
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
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Left column: branding + CTA */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="max-w-lg w-full">
          {/* <header className="mb-8">
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">PR Sentinal</h1>
            <p className="mt-2 text-sm text-gray-600">Continue with your GitHub account to manage pull request insights and CI signals.</p>
          </header> */}

          <main className="space-y-6">
            <h2 className="text-2xl font-semibold">Sign in to continue</h2>

            <button
              onClick={startGithubLogin}
              disabled={loading}
              aria-label="Continue with GitHub"
              className="w-[60vh] inline-flex items-center justify-center gap-3 px-4 py-3 rounded shadow hover:opacity-95 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                  </svg>
                </>
              ) : (
                "Continue with GitHub"
              )}
            </button>

            <p className="text-xs text-gray-500">
              By continuing you agree to the terms.
            </p>
          </main>
        </div>
      </div>

      {/* Right column: hero image for larger screens */}
      <div className="hidden md:block md:w-1/2 h-screen">
        {/* Replace /auth-hero.jpg with your own asset in the public/ folder */}
        <div
          className="h-full w-full bg-center bg-cover"
          style={{ backgroundImage: "url('/auth-hero.jpg')" }}
          role="img"
          aria-label="Illustration of laptops and screens"
        />
      </div>

      {/* On small screens show a compact hero image above or below content if desired */}
      <div className="md:hidden w-full">
        <img src="/auth-hero.jpg" alt="Laptops and screens" className="w-full h-48 object-cover" />
      </div>
    </div>
  );
}
