'use client'

import Link from 'next/link'
import Logo from '@/components/brand/logo'


export const Header = () => {
  return (
    <nav
      className="fixed top-0 left-0 z-50 w-full h-16"
    >
      <div className="container mx-auto px-3">
        <div className="flex h-16 items-center justify-between">
          <div className="flex-shrink-0">
            <Link href="/" className="flex items-center">
              <div className="flex items-center justify-center">
                <Logo/>
              </div>
            </Link>
          </div>
          {/* Add right-side actions here if needed */}
        </div>
      </div>
    </nav>
  )
}