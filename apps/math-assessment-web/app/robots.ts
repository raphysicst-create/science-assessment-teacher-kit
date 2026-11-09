import type { MetadataRoute } from "next";
import { SITE_URL } from "./lib/site";

const AI_CRAWLERS = [
  "GPTBot",
  "ChatGPT-User",
  "CCBot",
  "ClaudeBot",
  "Claude-Web",
  "anthropic-ai",
  "Google-Extended",
  "PerplexityBot",
  "cohere-ai",
  "Bytespider",
  "Amazonbot",
  "Applebot-Extended",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/" },
      ...AI_CRAWLERS.map((userAgent) => ({ userAgent, disallow: "/" })),
    ],
    sitemap: new URL("/sitemap.xml", SITE_URL).href,
  };
}
