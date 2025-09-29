import { publicProcedure } from "@/lib/trpc";
import z from "zod";

export const getGithubOAuthUrlProcedure = publicProcedure.query(async () => {});
