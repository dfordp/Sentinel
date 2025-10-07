import { LandingNavbar } from "@/components/landing-navbar"
import { LandingHero } from "@/components/landing-hero"
import { LandingWaitlist } from "@/components/landing-waitlist"
import { LandingProblemSolution } from "@/components/landing-problem-solution"
import { LandingHowItWorks } from "@/components/landing-how-it-works"
import { LandingDemo } from "@/components/landing-demo"
import { LandingRoadmap } from "@/components/landing-roadmap"
import { LandingFooter } from "@/components/landing-footer"

export default function Page() {
  return (
    <main className="bg-[#0a0a0a]">
      <LandingNavbar />
      <LandingHero />
      <LandingWaitlist />
      <LandingProblemSolution />
      <LandingHowItWorks />
      <LandingDemo />
      <LandingRoadmap />
      <LandingFooter />
    </main>
  )
}
