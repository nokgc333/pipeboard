const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

/** アップロードファイルのフロント側バリデーション（バックの二重チェック、仕様書§6.3）。 */
export function validateUploadFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  const hasAllowedExtension = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  if (!hasAllowedExtension) {
    return "対応していないファイル形式です";
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "ファイルサイズは10MBまでです";
  }
  return null;
}
