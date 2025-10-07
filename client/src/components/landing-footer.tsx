import Link from "next/link"

export function LandingFooter() {
  return (
    <footer className="border-t bg-card">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
          <p className="text-muted-foreground">{"Built by maintainers, for maintainers."}</p>
          <nav className="flex items-center gap-4">
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground">
              GitHub Repo
            </Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground">
              Contact
            </Link>
            <Link href="#" className="text-sm text-muted-foreground hover:text-foreground">
              Join Waitlist
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}
