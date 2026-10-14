import "@fontsource-variable/nunito-sans";
import "@fontsource-variable/outfit";
import "./globals.css";

export const metadata = {
  title: "Numa · Tutor de Precálculo",
  description: "Un tutor que te acompaña a comprender Precálculo paso a paso.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
