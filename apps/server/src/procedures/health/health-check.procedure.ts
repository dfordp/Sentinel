import { publicProcedure } from "@/lib/trpc";

export const healthCheckProcedure = publicProcedure.query(() => {
    return {
        message: "Hello from PR Sentinel!"
    }
})
