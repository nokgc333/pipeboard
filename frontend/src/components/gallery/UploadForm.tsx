"use client";

import { useRef, useState } from "react";
import { validateUploadFile } from "@/domain/upload/upload-validation";

export function UploadForm({ onUpload }: { onUpload: (file: File) => void }) {
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp"
        aria-label="バージョン画像を選択"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          const validationError = validateUploadFile(file);
          if (validationError) {
            setError(validationError);
            return;
          }
          setError(null);
          onUpload(file);
          if (inputRef.current) inputRef.current.value = "";
        }}
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
