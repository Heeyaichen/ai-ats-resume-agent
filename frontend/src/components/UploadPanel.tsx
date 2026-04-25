/** File upload panel with validation. */

import React, { useRef, useState } from "react";
import { Upload, FileText, AlertCircle } from "lucide-react";

const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

interface Props {
  disabled?: boolean;
  onFileSelected: (file: File) => void;
}

const UploadPanel: React.FC<Props> = ({ disabled, onFileSelected }) => {
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return "Only PDF and DOCX files are accepted.";
    }
    if (file.size > MAX_SIZE_BYTES) {
      return "File exceeds the 10 MB limit.";
    }
    return null;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const err = validate(file);
    if (err) {
      setError(err);
      setFileName(null);
      return;
    }
    setError(null);
    setFileName(file.name);
    onFileSelected(file);
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-label">
        Resume
        <span className="ml-1 font-normal text-secondary">
          PDF or DOCX, up to 10 MB
        </span>
      </label>

      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-dashed border-glass-border bg-glass-panel px-4 py-8 text-secondary transition-colors hover:border-accent/40 hover:text-accent disabled:pointer-events-none disabled:opacity-40"
      >
        {fileName ? (
          <>
            <FileText className="h-5 w-5" />
            <span className="truncate max-w-xs text-label">{fileName}</span>
          </>
        ) : (
          <>
            <Upload className="h-5 w-5" />
            <span>Choose file</span>
          </>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        onChange={handleChange}
        className="hidden"
        disabled={disabled}
      />

      {error && (
        <p className="flex items-center gap-1.5 text-sm text-danger">
          <AlertCircle className="h-4 w-4" />
          {error}
        </p>
      )}
    </div>
  );
};

export default UploadPanel;
