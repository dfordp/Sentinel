import { integrationStore } from "@/integrations";
import { publicProcedure } from "@/lib/trpc";

export const getGithubOAuthUrlProcedure = publicProcedure.query(async () => {
	const url = await integrationStore.githubOAuth.getOAuthUrl();

	return {
		url,
	};
});
