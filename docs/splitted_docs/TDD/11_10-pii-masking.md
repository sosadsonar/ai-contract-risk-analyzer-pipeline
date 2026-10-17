<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 10. PII Masking | 1940 ký tự | trước: 10_9-scope-precheck.md | sau: 12_11-clause-segmentation.md -->

# 10. PII Masking

## 10.1 PII type và placeholder

| Type | Short code | Tag ưu tiên | Ý nghĩa |
|---|---|---|---|
| PERSON_NAME | N | <NAME> | Họ tên |
| DATE_OF_BIRTH | D | <DOB> | Ngày sinh |
| NATIONAL_ID_OR_PASSPORT | I | <ID> | CCCD/hộ chiếu |
| RESIDENTIAL_ADDRESS | R | <ADDR> | Địa chỉ cư trú |
| PHONE | P | <PHONE> | Số điện thoại |
| EMAIL | E | <EMAIL> | Email |
| BANK_ACCOUNT | B | <BANK> | Số tài khoản |
| LEGAL_ENTITY | O | <ORG> | Tên pháp nhân |

```python
def mask_value(text, pii_type):
    n = len(text)  # Unicode code points after NFC
    tag = TYPE_TAG[pii_type]  # ASCII tag
    if n >= len(tag):
        return tag + "_" * (n - len(tag))
    return TYPE_SHORT_CODE[pii_type] * n

assert len(mask_value(value, pii_type)) == len(value)
```

Ví dụ: `nguyenvana@gmail.com` -> `<EMAIL>____________` với đúng cùng số code point. Tên rất ngắn 2 ký tự -> `NN`. Dùng `_` thay ký tự block để giảm token; prompt chỉ giải thích type tag/code, không truyền original value.

## 10.2 Detection order

* Regex/high-precision trước: email, phone, national ID/passport, bank account, date-of-birth với anchor, địa chỉ với anchor.
* Heuristic entity sau: họ tên và tên pháp nhân dựa trên anchor như "Ông/Bà", "Người lao động", "Đại diện", "Công ty", "MST"; chỉ mask span value, không mask từ vai trò.
* Preserve-list: lương/phụ cấp, thời hạn/ngày hiệu lực không phải DOB, giờ làm, chức danh, tỉnh/thành phố cấp tỉnh, từ NLĐ/NSDLĐ.
* Overlap resolution: sort theo start, sau đó ưu tiên span dài hơn và type high-confidence; không cho overlap sau resolve.
* Không sử dụng cloud NER/LLM. NER local chỉ được thêm nếu privacy metric trên D1 không đạt, theo SRS OI-12.

## 10.3 Boundary safety

Masker trả pii_spans[{type,start,end}]. Segmenter phải gọi boundary_guard(pos): false nếu start < pos < end của bất kỳ pii_span. Nếu regex heading tạo boundary trong placeholder thì boundary dời ra đầu/end placeholder gần nhất hoặc bỏ match.
