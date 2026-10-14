import "@fontsource-variable/nunito-sans";
import "@fontsource-variable/outfit";
import "./globals.css";

export const metadata = {
  title: "PATI · Tutora inteligente de Precálculo",
  description: "Tutoría adaptativa consciente de prerrequisitos para aprender Precálculo paso a paso.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
