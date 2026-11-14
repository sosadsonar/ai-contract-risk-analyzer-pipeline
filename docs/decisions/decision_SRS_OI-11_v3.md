# Quyết định và phương pháp xử lý --- SRS OI-11 (DOCX numbering)

-   **Trạng thái:** Đã thống nhất phương án A --- Visual text fidelity; đồng thời mở rộng `structure_parser` để nhận diện số La Mã và bullet `+`.
-   **Phạm vi:** Ghi nhận quyết định, tiêu chí nghiệm thu và cách xử lý
    giới hạn OI-11. Không phải yêu cầu sửa code hay cập nhật tài liệu
    khác.

## 1. Quyết định

Chọn **Phương án A --- Visual text fidelity**.

DOCX extractor phải bảo toàn nội dung văn bản hiển thị, bao gồm
numbering/bullet do Word sinh tự động và marker được người soạn gõ trực
tiếp. Extractor không có trách nhiệm khôi phục cây hierarchy đầy đủ của
Multilevel List.

Với numbering gõ tay, marker đã là text thường trong paragraph.
Extractor chỉ cần giữ nguyên: không xóa, không tự thêm và không nhân
đôi.

Với numbering tự động, extractor materialize marker vào văn bản đầu ra
trong phạm vi format hỗ trợ. Không được thêm marker lần nữa nếu marker
tương ứng đã có trong text. Kiểm thử phải phát hiện marker bị thiếu hoặc
nhân đôi, nhất là trường hợp numbering tự động kết hợp với text gõ tay.

## 2. Phạm vi format

Format numbering tự động nằm trong phạm vi kiểm chứng:

-   Decimal.
-   Decimal-zero.
-   Chữ cái.
-   Số La Mã (các numeral La Mã hợp lệ, ví dụ `I.`, `II.`, `III.`, `IV.`; nhận diện không phân biệt hoa/thường).
-   Bullet, bao gồm `-`, `–`, `•` và `+`.

`structure_parser` phải nhận diện số La Mã thành một nhóm marker riêng (`roman`) để kiểm tra chuỗi La Mã; không nhầm `I.`/`II.` với nhóm chữ cái đơn. Bullet `+` được nhận diện như một biến thể của nhóm `dash` hiện có, không cần tạo loại cấu trúc bullet mới.

Các dạng như `Điều 1.`, `1)`, `I.`, `-` và `+` nếu được gõ trực tiếp là
text gốc; extractor không cần phân tích chúng thành metadata numbering.

Format tự động ngoài danh sách hỗ trợ được ghi nhận là **không hỗ trợ**.
Extractor không đoán format, suy diễn marker hoặc dựng cấu trúc thay cho
metadata không được hỗ trợ.

## 3. Hợp đồng đầu ra giữa extractor và structure_parser

Extractor không xuất `level`, `parent` hoặc loại numbering. Tuy nhiên,
marker trong văn bản đầu ra phải ở dạng mà `structure_parser` nhận diện
được:

-   Marker nằm ở đầu dòng.
-   Marker khớp một trong các pattern parser hỗ trợ, bao gồm Roman numerals và bullet `+` sau khi mở rộng parser theo quyết định này.
-   Nội dung paragraph sau marker được giữ nguyên.
-   Không tạo marker trùng với marker đã có trong text.

Đây là hợp đồng đầu ra giữa extractor và parser, không phải yêu cầu
extractor xuất metadata cấu trúc.

### Kiểm chứng bắt buộc

Với mỗi fixture DOCX:

1.  Chạy DOCX extraction.
2.  So sánh `canonical_text` với `expected canonical text` đã được đối
    chiếu với tài liệu gốc/hiển thị trong Word.
3.  Đưa kết quả extraction qua `structure_parser`.
4.  So sánh `level` và `parent` do parser nhận diện với expected.
5.  Kiểm tra marker không bị thiếu hoặc nhân đôi, đặc biệt khi numbering
    tự động và text gõ tay cùng xuất hiện.

Bộ fixture tối thiểu phải bao gồm:

-   Multilevel List.
-   Bullet.
-   Numbering gõ tay.
-   Trường hợp mixed: numbering tự động và marker gõ tay trong cùng tài
    liệu.

Expected text phải được xác minh với tài liệu gốc, không được tạo ra chỉ
bằng cách sao chép output của extractor.

## 4. Giới hạn đã biết: parser bỏ qua nhóm chỉ có một mục hoặc nhóm không đủ sequence

`structure_parser` giữ nguyên quy tắc độ tin cậy của các weak markers; việc
bổ sung Roman numerals và `+` không nới lỏng điều kiện này:

-   `numbered`: cần ít nhất hai mục anh em, bắt đầu từ `1` và liên tiếp.
-   `lettered`: cần ít nhất hai mục anh em, bắt đầu từ `a` và liên tiếp.
-   `roman`: cần ít nhất hai mục anh em, bắt đầu từ `I`/`i`; từng marker
    phải là Roman numeral hợp lệ và các giá trị phải liên tiếp (`I, II,
    III, IV...`).
-   `dash` (gồm `-`, `–`, `•`, `+`): cần ít nhất hai mục anh em; không
    có điều kiện đánh số liên tiếp.

Hệ quả: nếu Word numbering được materialize không đầy đủ --- ví dụ một
mục dùng format không hỗ trợ khiến marker không xuất hiện --- nhóm còn
lại có thể bị đứt chuỗi và parser có thể bỏ qua cả nhóm. Một mục đơn lẻ
cũng không được coi là ranh giới clause theo quy tắc hiện tại.

Đây là giới hạn downstream được chấp nhận trong OI-11. `level` và `parent`
do parser trả về là cấu trúc suy luận từ chuỗi marker và stack hiện tại;
chúng không phải bản tái tạo chính xác metadata level/hierarchy của Word.

### Cách xử lý trong phạm vi quyết định hiện tại

-   Ghi nhận đây là **hạn chế đã biết** của tổ hợp extractor--parser;
    không tuyên bố hỗ trợ đầy đủ nhóm numbering bị thiếu marker.
-   Với format tự động ngoài phạm vi, không đoán hoặc tự tạo marker để
    vá chuỗi numbering.
-   Roman list chỉ được nhận diện khi tạo thành nhóm anh em đủ điều kiện;
    không tự nhận diện một dòng `I.` hoặc `II.` đơn lẻ làm clause boundary.
-   Bullet `+` được gom vào nhóm `dash`; một dòng `+` đơn lẻ không tạo
    clause boundary.
-   Nếu marker không được materialize đầy đủ hoặc parser bỏ qua nhóm,
    ghi nhận rõ đó là trường hợp không được hỗ trợ; không dùng kết quả
    parser làm bằng chứng cấu trúc clause đã được khôi phục đúng.
-   Acceptance test cần có trường hợp numbering bị đứt/thiếu marker để
    xác nhận giới hạn được phát hiện và ghi nhận, không âm thầm coi là
    thành công.
-   Nếu sau này cần nhận diện danh sách một mục hoặc danh sách bị đứt
    chuỗi, thay đổi chính sách `structure_parser` phải được xem xét như
    issue/phạm vi riêng, không tự động gộp vào OI-11.

## 5. Ngoài phạm vi

OI-11 không yêu cầu extractor:

-   Xuất `level`, `parent` hoặc loại numbering/bullet.
-   Khôi phục cây hierarchy đầy đủ của Multilevel List.
-   Suy luận cấu trúc từ indent/khoảng trắng khi không có marker hoặc
    metadata được hỗ trợ.
-   Hỗ trợ mọi custom numbering format, picture bullet hoặc symbol font
    đặc biệt.
-   Tự sửa hoặc suy đoán marker bị thiếu do format không hỗ trợ.

## 6. Điều kiện nghiệm thu và kết luận

OI-11 chỉ được xem xét đóng khi có bằng chứng đáp ứng đồng thời:

1.  Mỗi fixture có `canonical_text` khớp expected text đã đối chiếu với
    tài liệu gốc.
2.  Fixture bao gồm Multilevel List, bullet (`-`, `–`, `•`, `+`) và
    numbering gõ tay; có trường hợp mixed để kiểm tra không mất/nhân đôi
    marker. Có fixture kiểm tra Roman sequence, tối thiểu `I.`, `II.` và
    một chuỗi có numeral chuyển tiếp như `III.`/`IV.`.
3.  Marker đầu dòng thuộc pattern mà `structure_parser` nhận diện, gồm
    Roman numerals và bullet `+`.
4.  Test tích hợp chạy extraction rồi `structure_parser`, sau đó so sánh
    `level` và `parent` với expected theo quy tắc suy luận hiện có của
    parser. `level`/`parent` là cấu trúc parser suy ra từ chuỗi marker;
    không được hiểu là khôi phục chính xác Word list-level metadata.
5.  Regression tests phải bao gồm hai lỗi đã tái hiện trong technical
    review: effective-level/format override khi thay placeholder và
    `lvlRestart=0` không được reset sai.
6.  Nếu sửa numbering làm thay đổi `canonical_text`, phải tăng/quản lý
    extraction version phù hợp và tính lại mọi spans phụ thuộc; không dùng
    lại offset được tạo từ canonical text cũ.
7.  Với fixture có clause nằm sau marker numbering được materialize,
    kiểm tra span downstream vẫn trỏ đúng substring trong canonical text;
    highlight phải phủ đúng substring đó sau ánh xạ offset code point →
    UTF-16 ở frontend. Nếu canonical text thay đổi, spans phải được tính
    lại theo đúng extraction version mới, không tái sử dụng offset cũ.
8.  Format ngoài phạm vi và giới hạn parser tại Mục 4 được ghi nhận minh
    bạch; không tuyên bố hỗ trợ vượt quá bằng chứng.

**Kết luận:** Chốt phương án A --- Visual text fidelity; mở rộng
`structure_parser` để nhận diện Roman numerals và bullet `+`. Giữ nguyên
điều kiện weak group tối thiểu hai mục, quy tắc chuỗi liên tiếp cho
numbered/lettered/roman và cách suy luận level/parent hiện tại; không khôi
phục đầy đủ hierarchy của Word. Các giới hạn singleton/nhóm numbering
bị đứt được chấp nhận và phải ghi nhận. Hai lỗi DOCX đã tái hiện cùng
extraction-version/span invalidation là điều kiện nghiệm thu, không phải
lý do thay đổi phương án A.
