import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { BrandWordmark } from "../components/Logo";
import { RouteNetworkGraphic } from "../components/RouteNetworkGraphic";

export function AuthLayout({
  children,
  panelTitle,
  panelDescription,
}: {
  children: ReactNode;
  panelTitle: string;
  panelDescription: string;
}) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-paper">
      <div className="hidden lg:flex flex-col justify-between bg-primary-dark text-paper p-10 xl:p-14">
        <BrandWordmark className="text-paper" />
        <div className="flex flex-col items-start gap-8">
          <RouteNetworkGraphic />
          <div className="max-w-sm">
            <h2 className="text-2xl font-semibold text-paper mb-2">{panelTitle}</h2>
            <p className="text-paper/70 leading-relaxed">{panelDescription}</p>
          </div>
        </div>
        <p className="text-sm text-paper/50">Phase 1 · Identity &amp; account foundation</p>
      </div>

      <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16 xl:px-20">
        <Link to="/" className="lg:hidden mb-10 self-start">
          <BrandWordmark />
        </Link>
        <div className="flex-1 flex flex-col justify-center max-w-sm w-full mx-auto lg:mx-0">{children}</div>
      </div>
    </div>
  );
}
