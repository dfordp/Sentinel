"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50)
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <div className="fixed left-0 right-0 top-0 z-50 flex justify-center px-4">
      <nav
        className={cn(
          "mt-4 w-full max-w-5xl rounded-2xl border transition-all duration-300 ease-out",
          scrolled
            ? "border-border bg-card/95 shadow-lg backdrop-blur-md"
            : "border-border/50 bg-transparent"
        )}
      >
        <div
          className={cn(
            "flex items-center justify-between transition-all duration-300",
            scrolled ? "px-6 py-3" : "px-6 py-4"
          )}
        >
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div className={cn(
              "text-xl font-bold transition-colors duration-300",
              scrolled ? "text-foreground" : "text-foreground"
            )}>
              PR Sentinel
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="hidden items-center space-x-8 md:flex">
            <Link
              href="#features"
              className={cn(
                "text-sm font-medium transition-colors duration-300",
                scrolled ? "text-muted-foreground hover:text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Features
            </Link>
            <Link
              href="#how-it-works"
              className={cn(
                "text-sm font-medium transition-colors duration-300",
                scrolled ? "text-muted-foreground hover:text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              How It Works
            </Link>
            <Link
              href="#demo"
              className={cn(
                "text-sm font-medium transition-colors duration-300",
                scrolled ? "text-muted-foreground hover:text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Demo
            </Link>
          </div>

          {/* CTA Buttons */}
          <div className="flex items-center space-x-3">
            <Button
              asChild
              variant="ghost"
              size="sm"
            >
              <Link href="/dashboard">Sign In</Link>
            </Button>
            <Button
              asChild
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Link href="#waitlist">Join Waitlist</Link>
            </Button>
          </div>
        </div>
      </nav>
    </div>
  )
}
