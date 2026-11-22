"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthForm, type AuthMode, type AuthValues } from "@/components/AuthForm";
import { errorMessage, getMe, login, register } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => { getMe().then(() => router.replace("/dashboard")).catch(() => undefined); }, [router]);

  async function handleSubmit(mode: AuthMode, values: AuthValues) {
    setMessage(null);
    try {
      if (mode === "register") await register(values.email, values.displayName, values.password);
      await login(values.email, values.password);
      router.replace("/dashboard");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  return <main><AuthForm onSubmit={handleSubmit} message={message} /></main>;
}
