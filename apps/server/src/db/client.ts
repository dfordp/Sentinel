import { PrismaClient } from "@/db/prisma";

// ! Before using with cloudflare workers comment this section out

const globalForPrisma = global as unknown as { prisma: typeof db };

export const db: PrismaClient = globalForPrisma.prisma || new PrismaClient();
