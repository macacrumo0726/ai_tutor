"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BookOpen, BrainCircuit, Sparkles } from "lucide-react";
import { MathBackdrop } from "@/components/MathBackdrop";
import { API_URL } from "@/lib/api";
import { getSession, saveSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [userId, setUserId] = useState("test");
  const [name, setName] = useState("test");
  const [pin, setPin] = useState("test");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (getSession()) router.replace("/tutor"); }, [router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/auth/${mode}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode === "login" ? { user_id: userId, pin } : { user_id: userId, display_name: name, pin }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "No fue posible iniciar sesión");
      saveSession(body); router.push("/tutor");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Error inesperado"); }
    finally { setBusy(false); }
  }

  return (
    <main className="login-page">
      <MathBackdrop />
      <section className="login-story">
        <div className="brand-mark"><Sparkles size={22}/> Numa</div>
        <div className="story-copy">
          <span className="eyebrow">TU COMPAÑERO DE PRECÁLCULO</span>
          <h1>Las matemáticas se entienden mejor <em>paso a paso.</em></h1>
          <p>Numa recuerda tu proceso, detecta qué conocimiento necesitas y adapta cada explicación a tu forma de aprender.</p>
          <div className="feature-row">
            <span><BrainCircuit/> Aprende contigo</span>
            <span><BookOpen/> Explica con evidencia</span>
          </div>
        </div>
        <div className="equation-ribbon"><span>y = mx + b</span><span>f(x) = x²</span><span>sen²θ + cos²θ = 1</span></div>
      </section>
      <section className="login-panel-wrap">
        <div className="login-card glass-card">
          <div className="mobile-brand"><Sparkles/> Numa</div>
          <span className="welcome-dot">●</span>
          <h2>{mode === "login" ? "¡Qué bueno verte!" : "Crea tu espacio"}</h2>
          <p>{mode === "login" ? "Continuemos desde donde quedaste." : "Empieza una experiencia de aprendizaje hecha para ti."}</p>
          <div className="mode-switch">
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Ingresar</button>
            <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Crear cuenta</button>
          </div>
          <form onSubmit={submit}>
            {mode === "register" && <label>¿Cómo quieres que te llamemos?<input value={name} onChange={e => setName(e.target.value)} autoComplete="name" /></label>}
            <label>Usuario<input value={userId} onChange={e => setUserId(e.target.value)} autoComplete="username" /></label>
            <label>PIN<input type="password" value={pin} onChange={e => setPin(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>
            {error && <div className="form-error">{error}</div>}
            <button className="primary-button" disabled={busy}>{busy ? "Preparando…" : mode === "login" ? "Entrar al tutor" : "Crear mi cuenta"}<ArrowRight size={19}/></button>
          </form>
          <small>Para el piloto usa un seudónimo y evita compartir información personal.</small>
        </div>
      </section>
    </main>
  );
}
