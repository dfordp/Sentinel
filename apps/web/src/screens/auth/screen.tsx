"use client"
import React from "react";
import { AuthCard } from "./components/auth-card";
import { AuthHero } from "./components/auth-hero";

export default function LoginScreen() {
  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background text-foreground font-primary">
      <AuthCard />
      <AuthHero />
    </div>
  );
}