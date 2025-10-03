import type { IntegrationTool } from "@/types/integration-tool";

export class GithubOAuth implements IntegrationTool {
	name = "Github OAuth";
	description =
		"This integration tools is used to control the whole application";
}
