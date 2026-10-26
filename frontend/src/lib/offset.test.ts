import { describe, expect, it } from "vitest";
import { buildCodePointIndex, cpLength, cpSlice } from "./offset";

describe("offset code point → UTF-16 (INV-12)", () => {
  it("văn bản BMP: trùng với slice thường", () => {
    const t = "Điều 1. Công việc";
    expect(cpSlice(t, 0, 6)).toBe(t.slice(0, 6));
  });

  it("ký tự ngoài BMP chiếm 2 đơn vị UTF-16", () => {
    const t = "a😀b"; // 3 code point, length UTF-16 = 4
    const idx = buildCodePointIndex(t);
    expect(idx).toEqual([0, 1, 3, 4]);
    expect(cpLength(idx)).toBe(3);
    expect(cpSlice(t, 1, 2, idx)).toBe("😀");
    expect(cpSlice(t, 2, 3, idx)).toBe("b"); // slice(2,3) thường sẽ trả nửa surrogate
  });

  it("clause là partition liên tiếp: ghép lại bằng đúng văn bản gốc", () => {
    const t = "Điều 1 😀\nĐiều 2";
    const idx = buildCodePointIndex(t);
    const mid = 8;
    expect(cpSlice(t, 0, mid, idx) + cpSlice(t, mid, cpLength(idx), idx)).toBe(t);
  });

  it("offset sai thì ném lỗi", () => {
    expect(() => cpSlice("abc", 0, 4)).toThrow(RangeError);
    expect(() => cpSlice("abc", 2, 1)).toThrow(RangeError);
  });
});
