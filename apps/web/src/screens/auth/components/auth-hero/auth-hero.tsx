"use client";

import Image from "next/image";
import Hero from "../../../../../public/auth-hero.jpg";

const AuthHero = () => {
	return (
		<div className="flex-1 h-screen lg:flex hidden items-center justify-center bg-primary font-secondary rounded-l-md">
			<Image
				src={Hero}
				width={1000}
				height={1000}
				alt="Auth Hero Image"
				className="w-full h-screen object-cover rounded-l-md"
			/>
		</div>
	);
};

export default AuthHero;