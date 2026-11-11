"""Kho dữ liệu giả cho P1 (N3, X-18). Không import gì từ app.*; viết độc lập, không sao chép regex của detector."""

SURNAMES = (
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô",
    "Dương", "Lý", "Đinh", "Đào", "Lương", "Trịnh", "Mai", "Tô", "Cao", "Hà", "Đoàn", "Lâm", "Tạ", "Quách",
    "Kiều", "Văn", "Hứa", "Thái", "Từ", "Lục", "Châu", "Ông", "Vương", "Khúc", "Lại", "Tăng", "Sầm", "Ung",
)
MIDDLE = (
    "Văn", "Thị", "Hữu", "Đức", "Minh", "Ngọc", "Xuân", "Thanh", "Thu", "Anh", "Hồng", "Quang", "Bảo", "Gia",
    "Khánh", "Thùy", "Kim", "Mỹ", "Phương", "Thảo", "Tuấn", "Đình", "Quỳnh", "Hoài", "Tố", "Yến",
)
GIVEN = (
    "An", "Bình", "Cường", "Dũng", "Hoa", "Hải", "Hạnh", "Hiếu", "Hương", "Huy", "Khải", "Lan", "Linh", "Long",
    "Mai", "Nam", "Nga", "Nhung", "Phúc", "Phong", "Quân", "Sơn", "Tâm", "Tú", "Tuyết", "Thắng", "Thủy", "Trang",
    "Trung", "Uyên", "Vinh", "Vy", "Yên", "Đạt", "Giang", "Hân", "Khang", "Kiên", "Liên", "Luân", "Nghĩa", "Oanh",
)
PROVINCES = (
    "Hà Nội", "Hải Phòng", "Đà Nẵng", "Cần Thơ", "Huế", "Nghệ An", "Thanh Hóa", "Bắc Ninh", "Hải Dương",
    "Đồng Nai", "Bình Dương", "Long An", "Khánh Hòa", "Lâm Đồng", "Quảng Ninh", "Tiền Giang", "Kiên Giang",
    "An Giang", "Bà Rịa - Vũng Tàu", "Thái Nguyên",
)
DISTRICTS = ("Quận 1", "Quận 3", "Quận Đống Đa", "Quận Cầu Giấy", "Quận Thanh Xuân", "Huyện Củ Chi",
             "Quận Ninh Kiều", "Thành phố Thủ Đức", "Quận Hải Châu", "Huyện Gia Lâm")
WARDS = ("phường Bến Nghé", "phường Láng Thượng", "phường Thượng Đình", "xã Tân Phú Trung",
         "phường Cổ Nhuế 1", "phường Hòa Cường Bắc", "xã Phú Mỹ")
STREETS = ("đường Lê Lợi", "đường Láng", "phố Huế", "đường Trần Cung", "đường Nguyễn Trãi", "ngõ 5 đường Láng",
           "đường Điện Biên Phủ", "đường Hai Bà Trưng")
COMPANY_FORMS = ("Công ty TNHH", "Công ty Cổ phần", "Công ty TNHH MTV", "CÔNG TY TNHH")
COMPANY_NAMES = (
    "Sao Mai", "Bình Minh", "Đông Hải", "Hoàng Long", "An Phát", "Thịnh Vượng", "Minh Khang", "Phú Quý",
    "Hưng Thịnh", "Thái Dương", "Kim Long", "Việt Phong", "Hòa Bình", "Tân Thành", "Đại Dương", "Ngọc Lâm",
    "Bảo Sơn", "Nam Việt", "Phương Đông", "Tường An", "Sông Hồng", "Hải Âu", "Trường Thịnh", "Anh Tuấn",
)
BANKS = ("Ngân hàng Kỹ thương", "Ngân hàng Ngoại thương", "Ngân hàng Công thương", "Ngân hàng Á Châu")
EMAIL_DOMAINS = ("example.com", "example.vn")
CCCD_PROVINCE_CODES = ("001", "002", "010", "019", "025", "031", "036", "040", "046", "048", "056", "062", "079", "092")
ID_ISSUE_PLACES = ("Cục Cảnh sát QLHC về trật tự xã hội", "Công an tỉnh Nghệ An", "Công an thành phố Hà Nội",
                   "Công an tỉnh Bình Dương", "Cục Cảnh sát QLHC và Dịch vụ hành chính công")
