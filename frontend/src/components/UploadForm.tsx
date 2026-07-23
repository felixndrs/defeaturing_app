import { useState } from "react";
import { useReview } from "../store";

export function UploadForm() {
  const uploadAndAnalyze = useReview((s) => s.uploadAndAnalyze);
  const [name, setName] = useState("Defeaturing Review");
  const [original, setOriginal] = useState<File | null>(null);
  const [defeatured, setDefeatured] = useState<File | null>(null);

  const ready = original && defeatured && name.trim();

  return (
    <div className="flex h-full items-center justify-center">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (ready) uploadAndAnalyze(name.trim(), original!, defeatured!);
        }}
        className="w-[28rem] rounded-xl border border-edge bg-panel p-6 shadow-xl"
      >
        <h1 className="text-xl font-semibold text-gray-100">AI Defeaturing Review</h1>
        <p className="mt-1 text-sm text-gray-400">
          Original- und vereinfachtes STEP-Modell hochladen.
        </p>

        <label className="mt-5 block text-sm text-gray-300">
          Projektname
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded border border-edge bg-black/40 p-2 text-gray-100 outline-none focus:border-amber-500"
          />
        </label>

        <FileField label="Original (STEP)" onChange={setOriginal} file={original} />
        <FileField label="Defeatured (STEP)" onChange={setDefeatured} file={defeatured} />

        <button
          type="submit"
          disabled={!ready}
          className="mt-6 w-full rounded bg-amber-600 py-2.5 font-medium text-white hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Analyse starten
        </button>
      </form>
    </div>
  );
}

function FileField({
  label,
  file,
  onChange,
}: {
  label: string;
  file: File | null;
  onChange: (f: File | null) => void;
}) {
  return (
    <label className="mt-4 block text-sm text-gray-300">
      {label}
      <input
        type="file"
        accept=".step,.stp"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        className="mt-1 block w-full text-sm text-gray-400 file:mr-3 file:rounded file:border-0 file:bg-edge file:px-3 file:py-1.5 file:text-gray-200 hover:file:bg-gray-700"
      />
      {file && <span className="text-xs text-gray-500">{file.name}</span>}
    </label>
  );
}
