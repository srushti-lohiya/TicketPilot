import Link from "next/link";
export default function NotFound() {
  return (
    <div className="panel p-8">
      <h1 className="text-xl font-semibold">Page not found</h1>
      <p className="my-4 text-muted-foreground">
        This workspace page does not exist.
      </p>
      <Link href="/" className="text-primary underline">
        Return to overview
      </Link>
    </div>
  );
}
