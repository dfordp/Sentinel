"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"

export function LandingWaitlist() {
  const [repoUrl, setRepoUrl] = useState("")
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    setIsSubmitting(false)
    setIsSubmitted(true)
    setRepoUrl("")
    setEmail("")
    
    // Reset success message after 3 seconds
    setTimeout(() => setIsSubmitted(false), 3000)
  }

  return (
    <section 
      id="waitlist" 
      className="relative overflow-hidden bg-background py-20 md:py-28"
      aria-labelledby="waitlist-title"
    >
      {/* Background gradient */}
      <div
        className="absolute inset-0 -z-10 opacity-30"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(1200px 600px at 50% 0%, var(--color-primary) 0%, transparent 60%)",
        }}
      />
      
      <div className="mx-auto max-w-4xl px-6">
        <div className="text-center">
          <h2 
            id="waitlist-title" 
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl"
          >
            Join the Waitlist
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            Be among the first to get actionable insights for your open source repository. 
            Enter your GitHub repo link and email to get early access.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mx-auto mt-10 max-w-2xl">
          <div className="space-y-4">
            <div>
              <label htmlFor="repo-url" className="sr-only">
                GitHub Repository URL
              </label>
              <input
                id="repo-url"
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/username/repository"
                required
                className="w-full rounded-xl border border-input bg-secondary px-6 py-4 text-foreground placeholder-muted-foreground backdrop-blur-sm transition-all duration-200 focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
              />
            </div>
            
            <div>
              <label htmlFor="email" className="sr-only">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                required
                className="w-full rounded-xl border border-input bg-secondary px-6 py-4 text-foreground placeholder-muted-foreground backdrop-blur-sm transition-all duration-200 focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
              />
            </div>

            <Button
              type="submit"
              size="lg"
              disabled={isSubmitting}
              className="w-full rounded-xl bg-primary py-6 text-base font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isSubmitting ? "Joining..." : "Join the Waitlist"}
            </Button>
          </div>

          {isSubmitted && (
            <div className="mt-4 rounded-xl border border-green-500/20 bg-green-500/10 px-4 py-3 text-center text-sm text-green-400">
              ✓ Successfully joined the waitlist! We&apos;ll be in touch soon.
            </div>
          )}
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          We respect your privacy. Your information will only be used to contact you about PR Sentinel.
        </p>
      </div>
    </section>
  )
}
