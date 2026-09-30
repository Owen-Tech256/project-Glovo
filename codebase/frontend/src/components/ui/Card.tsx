import type { HTMLAttributes } from "react";

export function Card({ className = "", children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-line bg-paper-raised ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className = "", children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`border-b border-line px-5 py-4 ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function CardBody({ className = "", children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`px-5 py-4 ${className}`} {...rest}>
      {children}
    </div>
  );
}
