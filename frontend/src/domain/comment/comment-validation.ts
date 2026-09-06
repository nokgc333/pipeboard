const MAX_COMMENT_LENGTH = 2000;

/** コメント本文のフロント側バリデーション（バックの二重チェック、仕様書§6.3）。 */
export function validateCommentBody(body: string): string | null {
  if (body.trim().length === 0) {
    return "コメントを入力してください";
  }
  if (body.length > MAX_COMMENT_LENGTH) {
    return `コメントは${MAX_COMMENT_LENGTH}文字までです`;
  }
  return null;
}
