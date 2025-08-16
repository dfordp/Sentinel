import { logger } from "@/utils/logger";
import { createFactory } from "hono/factory";

function getMicroTime() {
	return Number(process.hrtime.bigint()) / 1000;
}

export const networkLogger = createFactory().createMiddleware(
	async (context, next) => {
		const start = getMicroTime();
		await next();
		const duration = getMicroTime() - start;

		const formattedDuration =
			duration >= 1000
				? `${(duration / 1000).toFixed(3)}ms`
				: `${duration.toFixed(3)}µs`;

		logger.http(
			`[${context.req.method}] ${context.req.path} ${context.res.status} - ${formattedDuration}`,
		);
	},
);
