import { redirect } from "next/navigation";

import { appPassword, createSession, isAuthenticated } from "@/lib/session";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function firstParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}

async function loginAction(formData: FormData) {
  "use server";

  const password = String(formData.get("password") ?? "");
  if (password !== appPassword()) {
    redirect("/login?error=invalid_password");
  }

  await createSession();
  redirect("/");
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  if (await isAuthenticated()) {
    redirect("/");
  }

  const params = await searchParams;
  const hasError = firstParam(params, "error") === "invalid_password";

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f6f7f4] px-5 text-slate-950">
      <section className="w-full max-w-sm rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Zen Compta
        </p>
        <h1 className="mt-2 text-2xl font-semibold">Connexion</h1>
        <form action={loginAction} className="mt-6 space-y-4">
          <label className="block text-sm font-medium text-slate-600">
            Mot de passe
            <input
              autoComplete="current-password"
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
              name="password"
              required
              type="password"
            />
          </label>
          {hasError ? (
            <p className="text-sm font-medium text-red-700">
              Mot de passe incorrect.
            </p>
          ) : null}
          <button className="h-10 w-full rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
            Entrer
          </button>
        </form>
      </section>
    </main>
  );
}
