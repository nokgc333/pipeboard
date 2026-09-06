import { describe, expect, it } from "vitest";
import { validateUploadFile } from "./upload-validation";

function fakeFile(name: string, sizeBytes: number, type: string): File {
  const blob = new Blob([new Uint8Array(sizeBytes)], { type });
  return new File([blob], name, { type });
}

describe("validateUploadFile", () => {
  it("jpg/png/webpは許可される", () => {
    expect(validateUploadFile(fakeFile("a.png", 1000, "image/png"))).toBeNull();
    expect(validateUploadFile(fakeFile("a.jpg", 1000, "image/jpeg"))).toBeNull();
    expect(validateUploadFile(fakeFile("a.webp", 1000, "image/webp"))).toBeNull();
  });

  it("対応していない拡張子はエラーを返す", () => {
    expect(validateUploadFile(fakeFile("a.gif", 1000, "image/gif"))).toBe(
      "対応していないファイル形式です",
    );
  });

  it("10MBを超えるファイルはエラーを返す", () => {
    const oversized = fakeFile("a.png", 10 * 1024 * 1024 + 1, "image/png");
    expect(validateUploadFile(oversized)).toBe("ファイルサイズは10MBまでです");
  });

  it("10MBちょうどはOK", () => {
    const exact = fakeFile("a.png", 10 * 1024 * 1024, "image/png");
    expect(validateUploadFile(exact)).toBeNull();
  });
});
