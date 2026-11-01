---
description: 'MRL structure index scoped grant request and execution acceptance'
---
# MRL 結構索引授權修復｜2026-11-01

origin_signature: MrLiouWord
canonical_authority: Mr.liou
repository: dofaromg/MRL_ASI_system
parent_commit: 632683e7e880e9e938cd9e71d4d3fbc5a4db1e7d

本次工程指示授權追查、修正及建立待核准紀錄；不將條件式工程指示冒充已簽發的 runtime grant。
已查閱 Registry、Root Laws Law 30、Execution Laws、既有 PR #1/#2 與其中三份 Notion 來源。在已查範圍未找到適用的執行授權；不宣稱其他來源絕不存在授權。
原始失敗：https://github.com/dofaromg/MRL_ASI_system/actions/runs/41263488729。actor/triggering_actor 均為 dofaromg，event=schedule。
現行 active_grants=[]；原 Registry、索引與父系歷史保持原值。

## 可核准的具體範圍

請審查 ../config/MRL_STRUCTURE_INDEX_GRANT_REQUEST_20261101.json：僅 dofaromg/MRL_ASI_system 的 main、GitHub Actions、
actor/triggering_actor=dofaromg、手動 workflow_dispatch、深度 8，
scan/generate/upload 四個既有輸出至本庫 GitHub Actions artifact，保存 30 日。
有效期限提案為明示核准起 24 小時，啟用時記錄精確 UTC；不啟用排程、push、留言或本地執行。
approval、issued_by 與時間保持 null，status=pending；這些是明確未授權狀態，不是可執行的占位憑證。
Root Owner 需對此確切 request_id、範圍與期限提供可追溯明示核准；再由工程將正式記錄映射到原 Registry。
核准提案或合併此 PR 本身不自動啟用執行授權。

## 必要工程承接

本 PR 將授權程式 REPOSITORY/WORKFLOW 從 dofaromg/-Mr.liouagi 精確對齊 dofaromg/MRL_ASI_system，同步更新 synthetic tests 及既有 delivery payload hashes。歷史名稱保留於本紀錄與 Git，不擴大為任意環境值。
既有 PR #2 為拒絕呈現修正，並未建立 runtime grant；本 PR 不取代或覆寫該分支。
正式授權後，在正確修復分支補登錄、回歸測試與 PR；依現行治理完成 main 套用後，再執行 owner workflow_dispatch。
不得僅把 DENY/no-op 變綠視為索引成功。

## 驗收與回滾

本 PR CI 僅執行 synthetic tests，checkout exact PR head，不掃描 MRL 原樹、不上傳結構。
實際驗收仍須 scan、generate、upload 均成功，下載 artifact 核對四個非空檔案、SHA-256、大小及來源 SHA。
若新增或改名產物，先更新 Expected_File_List，不能默默省略。
撤銷時透過審查提交將正式 grant 設 revoked；保留原記錄、核准證據、輸出與 CI receipts；不重寫歷史。
完整索引修復目前為 BLOCKED_PENDING_ROOT_APPROVAL；未執行實際索引或宣告 DELIVERY_PASS。
