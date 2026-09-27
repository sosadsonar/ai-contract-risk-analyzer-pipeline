# Contributing Guide

## 1. Không push trực tiếp vào `main`

Quy trình:

main
→ tạo branch
→ code / sửa file
→ commit
→ push
→ Pull Request
→ review
→ merge

## 2. Bắt đầu task

```bash
git switch main
git pull origin main
git switch -c <ten-branch>

Ví dụ:
git switch -c data/risk-annotation-v01

3. Tên branch
Dùng:
data/<task>
ai/<task>
backend/<task>
frontend/<task>
docs/<task>
fix/<task>

4. Commit
Format:
<type>: <description>

Ví dụ:
data: update clause taxonomy
feat: add risk classifier
fix: correct parser bug
docs: update README

5. Pull Request
- Mọi thay đổi vào main phải qua PR
- Ít nhất 1 người review
- Không merge khi còn conflict
6. Tránh conflict
Không sửa cùng file với người khác nếu chưa trao đổi.
Nếu main có thay đổi mới:
git switch main
git pull origin main
git switch <ten-branch>
git merge main

7. Dataset
Không xóa version cũ:
clauses_v01.csv
clauses_v02.csv

Không sửa trực tiếp data/raw/.
8. Không commit secrets
Không commit:
.env
API key
password
AWS credentials

9. Merge
Ưu tiên:
Squash and merge

Không dùng:
git push --force


10. Quy trình bump khi có data mới 
cd ai_pipeline/data
git fetch origin
git log origin/main --oneline -5        # xem có gì mới, chọn đúng commit muốn lấy
git checkout <sha-cụ-thể>               # pin vào 1 commit rõ ràng, không checkout "origin/main"
cd ../..
git status                              # sẽ thấy: modified: ai_pipeline/data (new commits)
git add ai_pipeline/data
git commit -m "chore: bump data submodule to <sha-ngắn> - <lý do, vd: clauses_v0.3 + taxonomy moi>"
git push -u origin <nhánh-hiện-tại>