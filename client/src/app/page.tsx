import { LandingHero } from "@/components/landing-hero"
import { LandingProblemSolution } from "@/components/landing-problem-solution"
import { LandingHowItWorks } from "@/components/landing-how-it-works"
import { LandingDemo } from "@/components/landing-demo"
import { LandingRoadmap } from "@/components/landing-roadmap"
import { LandingFooter } from "@/components/landing-footer"

export default function Page() {
  return (
    <main>
      <LandingHero />
      <LandingProblemSolution />
      <LandingHowItWorks />
      <LandingDemo />
      <LandingRoadmap />
      <LandingFooter />
    </main>
  )
}
