import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Dhaka Nagorik AI",
  description: "Dhaka civic complaint assistant",
};

const themeBootstrapScript = `
(() => {
  const cookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith('dhaka-theme='));
  const theme = cookie ? decodeURIComponent(cookie.split('=')[1]) : 'dark';
  document.documentElement.dataset.theme = theme;
})();
`;

const themeToggleScript = `
(() => {
  const root = document.documentElement;
  const getTheme = () => root.dataset.theme || 'dark';
  const setTheme = (theme) => {
    root.dataset.theme = theme;
    document.cookie = 'dhaka-theme=' + encodeURIComponent(theme) + '; Path=/; Max-Age=31536000; SameSite=Lax';
    const buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach((button) => {
      const label = button.querySelector('[data-theme-label]');
      if (label) {
        label.textContent = theme === 'dark' ? 'Bright Mode' : 'Dark Mode';
      }
    });
  };

  setTheme(getTheme());

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const button = target.closest('[data-theme-toggle]');
    if (!button) {
      return;
    }

    const nextTheme = getTheme() === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
  });
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${manrope.variable} ${spaceGrotesk.variable}`} suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
          integrity="sha512-iecdLmaskl7CVkqkXNQ/ZH/XLlvWZOJyj7Yy7tcenmpD1ypASozpmT/E0iPtmFIB46ZmdtAc9eNBvH0H/ZpiBw=="
          crossOrigin="anonymous"
          referrerPolicy="no-referrer"
        />
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body className="min-h-screen antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeToggleScript }} />
        {children}
      </body>
    </html>
  );
}
