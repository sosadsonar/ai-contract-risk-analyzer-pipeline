// INV-12: API trả offset theo Unicode code point (đã NFC). JavaScript lại index theo UTF-16,
// nên ký tự ngoài BMP (emoji, một số chữ Hán…) chiếm 2 đơn vị → slice trực tiếp sẽ lệch.
// Quy tắc: mọi chỗ cắt/highlight canonical_text phải đi qua file này.

/** index[i] = vị trí UTF-16 của code point thứ i; phần tử cuối = text.length. */
export function buildCodePointIndex(text: string): number[] {
  const index: number[] = [];
  let u16 = 0;
  for (const ch of text) {
    index.push(u16);
    u16 += ch.length; // 1 (BMP) hoặc 2 (cặp surrogate)
  }
  index.push(u16);
  return index;
}

/** Số code point của text. */
export function cpLength(index: number[]): number {
  return index.length - 1;
}

/** Cắt theo code point [start, end). Truyền index đã build sẵn để tránh tính lại nhiều lần. */
export function cpSlice(
  text: string,
  start: number,
  end: number,
  index: number[] = buildCodePointIndex(text),
): string {
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start || end > cpLength(index)) {
    throw new RangeError(`Offset không hợp lệ: [${start}, ${end}) trên văn bản ${cpLength(index)} code point`);
  }
  return text.slice(index[start], index[end]);
}
