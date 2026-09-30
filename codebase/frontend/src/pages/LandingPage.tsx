import { Link } from "react-router-dom";
import { ArrowUpRight, Store, Bike, ShieldCheck, Truck, MapPin, Clock } from "lucide-react";
import { BrandWordmark } from "../components/Logo";
import { RouteNetworkGraphic } from "../components/RouteNetworkGraphic";
import { Button } from "../components/ui/Button";

const portals = [
  {
    label: "For businesses",
    description: "List your shop, manage branches, and reach nearby customers.",
    to: "/vendor",
    icon: <Store className="h-5 w-5" />,
  },
  {
    label: "For riders",
    description: "Pick up delivery jobs on your schedule and track your earnings.",
    to: "/rider",
    icon: <Bike className="h-5 w-5" />,
  },
  {
    label: "For platform admins",
    description: "Operate the marketplace: accounts, orders, and disputes.",
    to: "/admin",
    icon: <ShieldCheck className="h-5 w-5" />,
  },
];

const principles = [
  {
    icon: <MapPin className="h-5 w-5" />,
    title: "Built around real routes",
    body: "Every order is a path from a shop to a doorstep. We designed the platform around that path, not around generic checkout flows.",
  },
  {
    icon: <Clock className="h-5 w-5" />,
    title: "Fast to join, fast to run",
    body: "Customers, businesses, and riders each get an account built for what they actually do — no shared, one-size-fits-all dashboard.",
  },
  {
    icon: <Truck className="h-5 w-5" />,
    title: "One platform, three roles",
    body: "A single marketplace connects local businesses with riders and the customers around them, coordinated from one place.",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line">
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <BrandWordmark />
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-ink-soft">
            <Link to="/vendor" className="hover:text-ink transition-colors">For businesses</Link>
            <Link to="/rider" className="hover:text-ink transition-colors">For riders</Link>
            <Link to="/login" className="hover:text-ink transition-colors">Log in</Link>
          </nav>
          <Link to="/register">
            <Button size="sm">Create account</Button>
          </Link>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-6xl px-6 py-16 lg:py-24 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="font-display text-4xl sm:text-5xl font-semibold leading-[1.08] text-ink mb-6">
              Local shops, riders, and customers, on one route.
            </h1>
            <p className="text-lg text-ink-soft leading-relaxed mb-8 max-w-md">
              Routeley connects nearby businesses to the customers around them, and gets orders there
              through a network of independent riders.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link to="/register">
                <Button size="lg">Create a customer account</Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="secondary">Log in</Button>
              </Link>
            </div>
          </div>
          <div className="flex justify-center lg:justify-end">
            <RouteNetworkGraphic />
          </div>
        </section>

        <div className="border-t border-line" />

        {/* Principles */}
        <section className="mx-auto max-w-6xl px-6 py-16">
          <div className="grid sm:grid-cols-3 gap-10">
            {principles.map((item) => (
              <div key={item.title}>
                <div className="h-10 w-10 rounded-md bg-primary-soft text-primary-dark flex items-center justify-center mb-4">
                  {item.icon}
                </div>
                <h3 className="font-display text-lg font-semibold text-ink mb-2">{item.title}</h3>
                <p className="text-ink-soft leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="border-t border-line" />

        {/* Portals */}
        <section className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="font-display text-2xl font-semibold text-ink mb-8">Not a customer?</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {portals.map((portal) => (
              <Link
                key={portal.to}
                to={portal.to}
                className="group flex flex-col justify-between rounded-lg border border-line p-6 hover:border-primary/40 transition-colors"
              >
                <div>
                  <div className="h-9 w-9 rounded-md bg-ink/[0.05] text-ink-soft flex items-center justify-center mb-4 group-hover:bg-primary-soft group-hover:text-primary-dark transition-colors">
                    {portal.icon}
                  </div>
                  <h3 className="font-medium text-ink mb-1.5">{portal.label}</h3>
                  <p className="text-sm text-ink-soft leading-relaxed">{portal.description}</p>
                </div>
                <span className="inline-flex items-center gap-1 text-sm font-medium text-primary mt-5">
                  Learn more
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </span>
              </Link>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-6xl px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-ink-soft">
          <BrandWordmark className="text-ink-soft" />
          <p>© {new Date().getFullYear()} Routeley. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
