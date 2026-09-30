import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { BrandWordmark } from "../components/Logo";
import { Button } from "../components/ui/Button";

interface PortalLandingPageProps {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
  bullets: string[];
  registerTo?: string;
  registerLabel?: string;
}

export function PortalLandingPage({ icon, eyebrow, title, description, bullets, registerTo, registerLabel }: PortalLandingPageProps) {
  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line">
        <div className="mx-auto max-w-5xl px-6 py-5 flex items-center justify-between">
          <BrandWordmark />
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Back to Routeley
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-16 lg:py-24">
        <div className="h-11 w-11 rounded-md bg-primary-soft text-primary-dark flex items-center justify-center mb-6">
          {icon}
        </div>
        <p className="text-sm font-medium text-primary mb-3">{eyebrow}</p>
        <h1 className="font-display text-3xl sm:text-4xl font-semibold text-ink mb-4 leading-tight">{title}</h1>
        <p className="text-lg text-ink-soft leading-relaxed mb-8 max-w-xl">{description}</p>

        <ul className="space-y-3 mb-10">
          {bullets.map((bullet) => (
            <li key={bullet} className="flex items-start gap-3 text-ink-soft">
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
              <span>{bullet}</span>
            </li>
          ))}
        </ul>

        <div className="flex flex-wrap items-center gap-3">
          {registerTo && (
            <Link to={registerTo}>
              <Button size="lg">{registerLabel ?? "Create account"}</Button>
            </Link>
          )}
          <Link to="/login">
            <Button size="lg" variant="secondary">Log in</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
