import Image from "next/image";

/** Shared site header shown above every page: the SmartStudyAI logo (not a link). */
export function SiteHeader() {
  return (
    <header className="site-header">
      <Image
        src="/smartstudy-header.svg"
        alt="SmartStudyAI"
        width={1090}
        height={250}
        className="site-header-logo"
        unoptimized // SVG is already vector; the image optimiser does not process SVG files
        preload // top-of-page logo: fetch it early
      />
    </header>
  );
}
