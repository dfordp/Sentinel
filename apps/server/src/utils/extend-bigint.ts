export const extendBigint = () => {
	// @ts-ignore
	BigInt.prototype.toJson = function () {
		return this.toString();
	};
};
