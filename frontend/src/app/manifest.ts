import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "VisualMind AI·777",
    short_name: "VisualMind",
    description: "Panel de producción de novelas creadas con IA",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#071430",
    theme_color: "#071430",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
