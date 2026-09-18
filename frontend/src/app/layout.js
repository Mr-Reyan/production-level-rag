import "./globals.css";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });


export const metadata = {
  title: "Doc Q&A - RAG Document Assistant",
  description: "Chat with your PDF documents using RAG and pgvector",
};
import { Providers } from "./providers";

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${inter.className}  h-full antialiased`}
    >
       <body className="h-full bg-neutral-50 font-sans text-neutral-900 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
