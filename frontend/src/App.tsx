import { useState } from "react";
import type { Role } from "./api/types";
import Progress from "./pages/Progress";
import Result from "./pages/Result";
import Upload from "./pages/Upload";

type View = "UPLOAD" | "PROGRESS" | "RESULT";

export default function App() {
  const [session, setSession] = useState<{ id: string; role: Role } | null>(null);
  const [view, setView] = useState<View>("UPLOAD");

  function handleCreated(id: string, role: Role) {
    setSession({ id, role });
    setView("PROGRESS");
  }

  function handleReset() {
    setSession(null);
    setView("UPLOAD");
  }

  if (!session || view === "UPLOAD") {
    return <Upload onCreated={handleCreated} />;
  }

  if (view === "PROGRESS") {
    return (
      <Progress
        sessionId={session.id}
        role={session.role}
        onCompleted={() => setView("RESULT")}
        onReset={handleReset}
      />
    );
  }

  return <Result sessionId={session.id} onReset={handleReset} />;
}
