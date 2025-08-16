import { initTRPC, TRPCError } from "@trpc/server";
import type { Context } from "./context";
import { errorHandler } from "@/utils/error-handler";

export const t = initTRPC.context<Context>().create();

export const router = t.router;

export const errorHandlerMiddleware = t.middleware(async ({ next }) => {
	const response = await next();

	if (!response.ok) {
		throw errorHandler(response.error.cause);
	}

	return response;
});

export const publicProcedure = t.procedure.use(errorHandlerMiddleware);
