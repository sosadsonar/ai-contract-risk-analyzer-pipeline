"""One disposable, memory-limited PDF parser. No database/config imports."""
import ctypes
import json
import os
import sys


def limit_memory(megabytes):
    maximum = megabytes * 1024 * 1024
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
        return None
    if os.name != 'nt':
        raise RuntimeError('Native parser memory limits unsupported on this platform')
    from ctypes import wintypes
    class BasicLimits(ctypes.Structure):
        _fields_ = [('per_process_time',ctypes.c_longlong),('per_job_time',ctypes.c_longlong),
                    ('flags',wintypes.DWORD),('min_working_set',ctypes.c_size_t),
                    ('max_working_set',ctypes.c_size_t),('active_processes',wintypes.DWORD),
                    ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
    class IOCounters(ctypes.Structure):
        _fields_ = [(name,ctypes.c_ulonglong) for name in
                    ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('basic',BasicLimits),('io',IOCounters),('process_memory',ctypes.c_size_t),
                    ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE,wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    limits.basic.flags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    limits.process_memory = maximum
    if (not kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits))
            or not kernel.AssignProcessToJobObject(handle,kernel.GetCurrentProcess())):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise ctypes.WinError(error)
    return handle  # Keep job handle alive until this process exits.


def main():
    max_bytes, max_pages, max_chars, memory_mb = map(int, sys.argv[1:])
    # Reserve the IPC pipe for our bounded JSON only. Native parser diagnostics
    # must not become unlimited output buffered in the parent API process.
    output = os.fdopen(os.dup(sys.stdout.fileno()), 'w', encoding='ascii')
    with open(os.devnull, 'wb') as discard:
        os.dup2(discard.fileno(), sys.stdout.fileno())
    try:
        job_handle = limit_memory(memory_mb)
    except Exception:
        output.write(json.dumps({'capacity_error':'Parser memory limit unavailable'}))
        output.flush()
        return 2
    try:
        import pymupdf
        data = sys.stdin.buffer.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError('PDF exceeds upload byte limit')
        with pymupdf.open(stream=data, filetype='pdf') as document:
            if document.page_count > max_pages:
                raise ValueError('PDF exceeds page limit')
            pages = []
            count = 0
            for page in document:
                text = page.get_text()
                count += len(text) + bool(pages)
                if count > max_chars:
                    raise ValueError('PDF exceeds extracted text limit')
                pages.append(text)
            result = '\n'.join(pages)
        output.write(json.dumps({'text':result}, ensure_ascii=True))
        output.flush()
        return 0
    except (ValueError, RuntimeError, MemoryError):
        output.write(json.dumps({'error':'Invalid PDF or PDF resource limit exceeded'}))
        output.flush()
        return 1


if __name__ == '__main__':
    sys.exit(main())
