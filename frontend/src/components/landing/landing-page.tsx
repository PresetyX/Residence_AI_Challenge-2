"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { ConsentModal } from "./consent-modal";
import { FinalCta } from "./final-cta";
import { Hero } from "./hero";
import { Navbar } from "./navbar";
import { Showcase } from "./showcase";

export function LandingPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => Boolean(state.user));
  const [consentOpen, setConsentOpen] = useState(false);

  // Signed-in visitors skip consent and go straight to the chat.
  const handleSignIn = useCallback(() => {
    if (isAuthenticated) router.push("/chat");
    else setConsentOpen(true);
  }, [isAuthenticated, router]);

  return (
    <div className="relative overflow-x-clip">
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-violet-600 focus:px-4 focus:py-2"
      >
        Pular para o conteúdo
      </a>
      <Navbar isAuthenticated={isAuthenticated} onSignIn={handleSignIn} />
      <main id="conteudo">
        <Hero isAuthenticated={isAuthenticated} onSignIn={handleSignIn} />
        <Showcase />
        <FinalCta isAuthenticated={isAuthenticated} onSignIn={handleSignIn} />
      </main>
      <footer className="border-t border-purple-500/10 px-6 py-8 text-center text-sm text-muted">
        <p>Destrava · Contra a procrastinação · Projeto do AI Residence Challenge</p>
        <p className="mt-1 text-xs text-slate-500">
          Google Agenda é uma marca do Google LLC. Este projeto não é afiliado ao Google.
        </p>
      </footer>
      <ConsentModal open={consentOpen} onClose={() => setConsentOpen(false)} />
    </div>
  );
}

export interface SignInProps {
  isAuthenticated: boolean;
  onSignIn: () => void;
}
