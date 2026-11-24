"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GoogleIcon } from "@/components/ui/google-icon";
import type { SignInProps } from "./landing-page";

export function FinalCta({ isAuthenticated, onSignIn }: SignInProps) {
  return (
    <section aria-labelledby="cta-title" className="px-5 pt-8 pb-24">
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="glass glow relative mx-auto max-w-4xl overflow-hidden rounded-[2rem] px-6 py-14 text-center sm:px-12"
      >
        <div
          aria-hidden="true"
          className="animate-pulse-glow absolute -top-32 left-1/2 size-96 -translate-x-1/2 rounded-full bg-violet-600/40 blur-[90px]"
        />
        <div className="relative">
          <h2
            id="cta-title"
            className="font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl"
          >
            Qual projeto você vem adiando?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted">
            Conecte o seu Google Agenda, conte a meta e veja a semana se organizar em blocos de
            foco. Você continua no controle: edita tudo manualmente e revoga o acesso quando
            quiser.
          </p>
          <Button
            size="lg"
            onClick={onSignIn}
            className="mt-8"
            icon={
              isAuthenticated ? undefined : (
                <span className="grid size-7 place-items-center rounded-full bg-white">
                  <GoogleIcon className="size-4" />
                </span>
              )
            }
          >
            {isAuthenticated ? (
              <>
                Abrir o chat <ArrowRight className="size-4" aria-hidden="true" />
              </>
            ) : (
              "Entrar com o Google"
            )}
          </Button>
        </div>
      </motion.div>
    </section>
  );
}
