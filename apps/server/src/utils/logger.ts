import winston from "winston";

const levels = {
	error: 0,
	warn: 1,
	info: 2,
	http: 3,
	debug: 4,
};

const level = () => {
	const env = process.env["NODE_ENV"] || "development";
	const isDevelopment = env === "development";
	return isDevelopment ? "debug" : "http";
};

const colors = {
	error: "red",
	warn: "yellow",
	info: "cyan",
	http: "magenta",
	debug: "white",
};

winston.addColors(colors);

const format = winston.format.combine(
	winston.format.timestamp({ format: "YYYY-MM-DD HH:mm:ss" }),
	winston.format.colorize({ all: true, colors }),
	winston.format.printf(
		(info) => `${info["timestamp"]} ${info.level}: ${info.message}`,
	),
);

const transports = [new winston.transports.Console({ level: level() })];

/**
 * This is the function type for Custom logger that can be used for logging.
 *
 * It has five functions:
 *
 * i. error: It can be used to log errors. It has a red color.
 *
 * ii. warn -> It can be used to log warnings. It has a yellow color.
 *
 * iii. info -> It can be used to log info. It has a cyan color.
 *
 * iv. http -> It can be used to log http events. It has a magenta color.
 *
 * v. debug -> It can be used for debugging purposes. It has a white color. It cannot be used in production environment.
 */
export const logger = winston.createLogger({
	levels,
	format,
	transports,
});
