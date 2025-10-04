"use client"

import { Header } from "@/components/common/header";



export default function Landing() {
  
  return (
    <div className="min-h-screen flex flex-col">
      <Header/>
      <main>
        <div className="container mx-auto px-6 py-15 relative">
          Landing Page
        </div>
      </main>
    </div>
  );
}