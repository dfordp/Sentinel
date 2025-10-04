'use client'

import Link from 'next/link'
import { Zap } from 'lucide-react'
import { Chakra_Petch } from 'next/font/google'
import Logo from '@/components/brand/logo'

const chakraPetch = Chakra_Petch({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700']
})

export const Header = () => {
  return (
    <nav
      className="fixed top-0 left-0 z-50 w-full h-16 flex "
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