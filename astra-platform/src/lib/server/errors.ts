/** Message of an unknown thrown value (catch clauses are typed `unknown`). */
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
