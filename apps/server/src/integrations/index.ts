import { GithubOAuth } from "./github-oauth";

export const integrationStore = {
	githubOAuth: new GithubOAuth(),
};

Object.freeze(integrationStore);
