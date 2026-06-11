import { defineConfig } from "vitepress";

export default defineConfig({
  title: "CDN Traffic Report",
  description: "Browser automation + Claude Code skill for Akamai & CloudFront traffic reporting",
  base: "/cdn-traffic-report/",
  srcDir: ".",
  outDir: "../dist",
  head: [
    [
      "script",
      {},
      `(function(){try{var t=localStorage.getItem("lab.theme");document.documentElement.setAttribute("data-theme",t||"dark")}catch(e){}})()`,
    ],
  ],
  themeConfig: {},
});
