import { describe, expect, it } from "vitest";
import { validateCommentBody } from "./comment-validation";

describe("validateCommentBody", () => {
  it("空文字はエラーメッセージを返す", () => {
    expect(validateCommentBody("")).toBe("コメントを入力してください");
  });

  it("空白のみもエラーとして扱う", () => {
    expect(validateCommentBody("   ")).toBe("コメントを入力してください");
  });

  it("2000文字ちょうどはOK（null）", () => {
    expect(validateCommentBody("a".repeat(2000))).toBeNull();
  });

  it("2001文字はエラー", () => {
    expect(validateCommentBody("a".repeat(2001))).toBe("コメントは2000文字までです");
  });

  it("通常の文字列はOK（null）", () => {
    expect(validateCommentBody("ライティング要調整")).toBeNull();
  });
});
