import { healthCheckProcedure } from "@/procedures/health";
import { router } from "../lib/trpc";

export const appRouter = router({
  "/health/check": healthCheckProcedure
});
export type AppRouter = typeof appRouter;
