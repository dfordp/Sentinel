"use client"
import React from "react";
import { AuthCard } from "./components/auth-card";

export default function LoginScreen() {
  return (
    <div className="bg-background min-h-screen flex items-center justify-center">
      <AuthCard />
    </div>
  );
}