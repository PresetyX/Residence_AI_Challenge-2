"use client";

import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { GoogleIcon } from "@/components/ui/google-icon";
import { Logo } from "@/components/ui/logo";
import type { SignInProps } from "./landing-page";

const LINKS = [
  { href: "#capacidades", label: "Capacidades" },
  { href: "#arquitetura", label: "Arquitetura" },
  { href: "#automacao", label: "Automação" },
];

export function Navbar({ isAuthenticated, onSignIn }: SignInProps) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-40 transition-colors duration-300 ${
        scrolled ? "border-b border-purple-500/15 bg-ink-950/75 backdrop-blur-xl" : "border-b border-transparent"
      }`}
    >
      <nav
        aria-label="Navegação principal"
        className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5"
      >
        <a href="#topo" aria-label="Destrava, início">
          <Logo size="md" />
        </a>
        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-white/5 hover:text-white"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <Button
          variant="secondary"
          onClick={onSignIn}
          icon={isAuthenticated ? undefined : <GoogleIcon className="size-4" />}
        >
          {isAuthenticated ? (
            <>
              Abrir o chat <ArrowRight className="size-4" aria-hidden="true" />
            </>
          ) : (
            "Entrar"
          )}
        </Button>
      </nav>
    </header>
  );
}
