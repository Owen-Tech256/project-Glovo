import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "../components/ui/Button";
import { BrandWordmark } from "../components/Logo";

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-paper flex flex-col items-center justify-center px-6 text-center gap-6">
      <BrandWordmark />
      <div className="h-12 w-12 rounded-full bg-ink/[0.05] text-ink-soft flex items-center justify-center">
        <Compass className="h-5 w-5" />
      </div>
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink mb-2">This route doesn&apos;t exist</h1>
        <p className="text-ink-soft max-w-sm">
          The page you're looking for isn't part of the map yet. Let's get you back on route.
        </p>
      </div>
      <Link to="/">
        <Button>Back to home</Button>
      </Link>
    </div>
  );
}
