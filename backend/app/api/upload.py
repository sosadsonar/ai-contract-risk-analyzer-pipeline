"""Streaming multipart parser with strict aggregate and file byte budgets."""
from dataclasses import dataclass
from email.message import Message

from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from starlette.requests import ClientDisconnect, Request


@dataclass
class Upload:
    role: str | None = None
    filename: str | None = None
    signature: bytes = b""
    file_bytes: int = 0
    file_seen: bool = False
    error: str | None = None


async def parse_upload(request: Request, file_limit: int, on_role) -> Upload:
    upload = Upload()
    content_type, params = parse_options_header(request.headers.get("content-type", "").encode())
    boundary = params.get(b"boundary")
    if content_type != b"multipart/form-data" or not boundary or len(boundary) > 200:
        return upload
    field = ""
    headers: dict[bytes, bytes] = {}
    header_name = bytearray()
    complete = False
    header_value = bytearray()
    role_value = bytearray()
    total = 0

    def field_start():
        nonlocal field, headers, role_value
        field = ""
        headers = {}
        role_value = bytearray()

    def header_end():
        headers[bytes(header_name).lower()] = bytes(header_value)
        header_name.clear()
        header_value.clear()

    def headers_end():
        nonlocal field
        message = Message()
        message["content-disposition"] = headers.get(b"content-disposition", b"").decode("latin-1")
        field = message.get_param("name", header="content-disposition") or ""
        if field == "file":
            upload.file_seen = True
            upload.filename = message.get_param("filename", header="content-disposition")

    def data(data, start, end):
        payload = memoryview(data)[start:end]
        if field == "role":
            if len(role_value) + len(payload) <= 100:
                role_value.extend(payload)
        elif field == "file":
            upload.file_bytes += len(payload)
            if upload.file_bytes > file_limit:
                upload.error = "FILE_TOO_LARGE"
            if len(upload.signature) < 5:
                upload.signature += bytes(payload[:5 - len(upload.signature)])

    def field_end():
        if field == "role":
            upload.role = role_value.decode("utf-8", errors="replace") if len(role_value) <= 100 else None
            on_role(upload.role)

    def finished():
        nonlocal complete
        complete = True

    parser = MultipartParser(boundary, {
        "on_part_begin": field_start,
        "on_header_field": lambda d, s, e: header_name.extend(d[s:e]),
        "on_header_value": lambda d, s, e: header_value.extend(d[s:e]),
        "on_header_end": header_end,
        "on_end": finished,
        "on_headers_finished": headers_end,
        "on_part_data": data,
        "on_part_end": field_end,
    })
    try:
        async for chunk in request.stream():
            total += len(chunk)
            if total > file_limit + 65536:
                upload.error = "FILE_TOO_LARGE"
                break
            parser.write(chunk)
            if upload.error == "FILE_TOO_LARGE":
                break
        else:
            parser.finalize()
    except (ClientDisconnect, ValueError, RuntimeError):
        upload.error = upload.error or "UNSUPPORTED_FILE_TYPE"
    if not complete and upload.error is None:
        upload.error = "UNSUPPORTED_FILE_TYPE"
    if not upload.error and not (upload.file_seen and upload.filename and (
        (upload.filename.lower().endswith(".pdf") and upload.signature.startswith(b"%PDF-"))
        or (upload.filename.lower().endswith(".docx") and upload.signature.startswith(b"PK\x03\x04"))
    )):
        upload.error = "UNSUPPORTED_FILE_TYPE"
    return upload
