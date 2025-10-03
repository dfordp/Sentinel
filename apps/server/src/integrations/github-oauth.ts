import type { IntegrationTool } from "@/types/integration-tool";
import {
	GITHUB_OAUTH_CLIENT_ID,
	GITHUB_OAUTH_CLIENT_SECRET,
	HOST,
} from "@/utils/env";
import { OAuthApp } from "@octokit/oauth-app";
import { GITHUB_OAUTH_CALLBACK_PATH } from "constants/config";

export class GithubOAuth implements IntegrationTool {
	name = "Github OAuth";
	description =
		"This integration tools is used to control the whole application";

	githubApp: OAuthApp;

	constructor() {
		this.githubApp = new OAuthApp({
			clientType: "oauth-app",
			clientId: GITHUB_OAUTH_CLIENT_ID,
			clientSecret: GITHUB_OAUTH_CLIENT_SECRET,
			redirectUrl: `${HOST}${GITHUB_OAUTH_CALLBACK_PATH}`,
			defaultScopes: ["read:user", "user:email", "read:org"],
		});
	}

	async getOAuthUrl() {
		const response = this.githubApp.getWebFlowAuthorizationUrl({
			allowSignup: true,
			scopes: ["read:user", "user:email", "read:org"],
		});

		return response.url;
	}
}
