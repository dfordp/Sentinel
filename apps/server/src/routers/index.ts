import { healthCheckProcedure } from "@/procedures/health";
import { router } from "../lib/trpc";
import { getGithubOAuthUrlProcedure } from "@/procedures/auth/get-github-oauth-url.procedure";

export const appRouter = router({
	"health/check": healthCheckProcedure,
	"auth/github/oauth-url": getGithubOAuthUrlProcedure,
});
export type AppRouter = typeof appRouter;
