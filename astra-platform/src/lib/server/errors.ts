import { NextResponse } from 'next/server';

/** Message of an unknown thrown value (catch clauses are typed `unknown`). */
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * 500 answer for an unexpected failure in an API route. The cause is logged on the server;
 * the client only gets `message`, never exception text, which can carry file paths, SQL or
 * library internals.
 */
export function serverError(route: string, error: unknown, message: string): NextResponse<{ error: string }> {
  console.error(`[${route}] ${message}: ${errorMessage(error)}`);
  return NextResponse.json({ error: message }, { status: 500 });
}
