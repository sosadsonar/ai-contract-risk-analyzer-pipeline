<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 8. Session, State Machine và điều phối | 604 ký tự | trước: 08_7-kien-truc-du-lieu-va-luu-tru.md | sau: 10_9-llm-integration-design.md -->

# 8. Session, State Machine và điều phối

![](/diagrams/state_machine.png)

Analysis Orchestrator là component duy nhất được phép chuyển state. Các service trả typed result/error, không tự thay đổi state.

## 8.1 Single-session processing

* Backend có một global processing lock/semaphore capacity = 1.
* Lock được giữ trong thời gian VALIDATING hoặc PROCESSING.
* Upload mới khi lock bận bị từ chối SYSTEM_BUSY và không tạo session.
* Session đã COMPLETED/FAILED/REJECTED không giữ processing lock.
* Session store vẫn phải cô lập dữ liệu theo session_id, dù demo chỉ xử lý một phiên tại một thời điểm.
