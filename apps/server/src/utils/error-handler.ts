import { Prisma } from "@/db/prisma";
import { logger } from "./logger";
import { TRPCError } from "@trpc/server";
import { ZodError } from "zod";
import { JwtTokenExpired, JwtTokenInvalid } from "hono/utils/jwt/types";

export const errorHandler = (error: unknown) => {
	logger.error(`${error}`);
	if (error instanceof Prisma.PrismaClientKnownRequestError) {
		console.log(error.code);
		if (
			error.code === "P2002" &&
			Array.isArray(error.meta?.target) &&
			error.meta?.target.includes("email")
		) {
			return new TRPCError({
				message: "Admin with same email exists!!",
				code: "BAD_REQUEST",
			});
		}

		if (error.code === "P2002" || error.code === "P2014") {
			return new TRPCError({
				message: "Some unique item collision occurred!!",
				code: "BAD_REQUEST",
			});
		}

		if (error.code === "P2023") {
			return new TRPCError({
				message:
					"Either no data found or some inconsistent column data type found.",
				code: "BAD_REQUEST",
			});
		}

		if (error.code === "P2025") {
			return new TRPCError({
				message: "Data not found!",
				code: "NOT_FOUND",
			});
		}
	}

	if (error instanceof ZodError) {
		return new TRPCError({
			message: error.issues[0]?.message ?? "",
			code: "BAD_REQUEST",
		});
	}

	if (error instanceof JwtTokenInvalid || error instanceof JwtTokenExpired) {
		return new TRPCError({
			message: error.message,
			code: "UNAUTHORIZED",
		});
	}

	if (error instanceof TRPCError) {
		return error;
	}

	if (error instanceof Error) {
		return new TRPCError({
			message: error.message,
			code: "BAD_REQUEST",
		});
	}

	return new TRPCError({
		message: "Internal Server Error",
		code: "INTERNAL_SERVER_ERROR",
	});
};
