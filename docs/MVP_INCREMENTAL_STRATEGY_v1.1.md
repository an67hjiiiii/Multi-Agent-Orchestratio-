# Phần cập nhật plan v1.1 — MVP and Incremental Delivery Strategy

Bản trích đọc nhanh từ kế hoạch chính, ngày 05/09/2026. Nội dung gồm timeline đã thay đổi và toàn bộ mục 19 mới: bảng milestone, required modules/input-output/DoD/demo/metrics/LKG/go-no-go/scope-cut, feature flags, rollback, phân loại Critical Path/Supporting/Extension và checklist dừng dự án. Các tham chiếu mục 1–18 trỏ về kế hoạch chính; đặc tả nghiên cứu đầy đủ tiếp tục nằm ở đó.

Mọi nhãn DONE trong lịch là mục tiêu nghiệm thu, chưa phải trạng thái ứng dụng đã xác minh. Các thay đổi được đánh dấu [THÊM v1.1] / [CẬP NHẬT v1.1].

### 12.2. Lịch theo tuần và điều kiện hoàn tất

**[CẬP NHẬT v1.1 — thay lịch delivery, giữ phạm vi nghiên cứu]** Mốc DONE là mục tiêu có điều kiện nghiệm thu, chưa phải trạng thái đã đạt. M0–M3 trong mục này là milestone; ký hiệu M1–M5 ở mục 12.1 vẫn là mã thành viên.

| Tuần | Việc chính | Artifact/đầu ra | Gate |
|---|---|---|---|
| W1 | Khóa bài toán/domain, calibration, schema; ráp slice nhập text → local answer; annotation starter | Research brief, contract v0, model/source manifest, rubric nháp | Slice đầu không phụ thuộc module P/N/O; chưa gắn nhãn M0 nếu thiếu retrieval/citation |
| W2 | Hoàn tất ingestion → Vanilla RAG A → citation → basic trace; 12–20 case development | **M0 DONE**, release manifest và LKG M0; source viewer tối thiểu | Qua DoD M0 mục 19.2; khởi động lại và chạy bằng local LLM thật |
| W3 | Decomposition, 3 profile, assignment, task-specific RAG, executor tối thiểu, synthesis | **Multi-agent baseline B end-to-end**, A vẫn chạy; development 32 case; LKG W3 | Case đa domain hoàn tất từ input tới answer/trace; dependency không được âm thầm bỏ |
| W4 | P-lite + Planning KB chạy trong pipeline; registry snapshot; annotation validation | **P chạy end-to-end**, LKG W4; validation 28 case | P bật/tắt thể hiện trong effective config và trace; đây là increment, chưa coi C-full đã hoàn tất |
| W5 | O-lite: relevance, exact/span dedup, budget; N rules-only bảo thủ; A/B/C cùng harness | Candidate M1 runnable, selected/dropped evidence log; LKG sau gate | O không chỉ là placeholder; giữ evidence chung cần thiết; dataset tiếp tục được annotate |
| W6 | Ổn định P-lite/O-lite, synthesis, trace/metrics; thêm dần O-full sau flag nếu không phá slice | **M1 DONE**, A/B/C có báo cáo pilot development/validation; 120 case annotation vòng 1; LKG M1 | Đạt toàn bộ DoD M1; phần O-full chưa ổn được tắt, không trì hoãn bản research MVP |
| W7 | Tiến tới M2: P/N/O full, DAG dependency đầy đủ, C−P/C−N/C−O; annotation vòng 2 | Candidate M2 end-to-end, six-condition pilot, agreement và robustness report | Tune chỉ trên development/validation; M1 vẫn là bản quay về nếu candidate lỗi |
| W8 | Hoàn thiện/tích hợp full core, audit benchmark/harness, preregistration và freeze | `m2-test-ready` LKG; frozen manifest/code/config/corpus/labels | Qua G4 trước main test; test-ready chưa đồng nghĩa M2 DONE vì còn kết quả/chấm/thống kê |
| W9 | Main experiment và blind grading theo protocol | Raw runs, ledger, packets ẩn danh; checkpoint có thể resume | Giữ nguyên model/corpus/hardware và config đã freeze giữa conditions |
| W10 | Hoàn tất runs, chấm, ablation, statistics, failure analysis | Results/CI/denominators reconcile; candidate **M2 DONE** | Chưa đủ dữ liệu hoặc analysis thì tiếp tục W11, không công bố M2 complete sớm |
| W11 | Nghiệm thu M2, bounded claims, report, demo và phục hồi LKG | **M2 DONE** sau khi đủ DoD; LKG M2 bất biến | M3 chỉ được cân nhắc sau M2 ổn và phần báo cáo/bảo vệ đã có đủ thời gian |
| W12 | Tái lập từ release, diễn tập, bàn giao | Final report/slides/demo/reproduction package | M3 không bắt buộc; nếu không đủ buffer thì để sau 12 tuần, không ảnh hưởng nghiệm thu |

**[CẬP NHẬT v1.1]** Critical path: **M0 runnable → B runnable → P runnable → O-lite + A/B/C có đánh giá (M1) → P/N/O full + DAG + ablations → freeze → main experiment/chấm/thống kê (M2)**. Corpus, dataset, rubric và evaluation harness đi cùng từng slice từ W1–2; không đẩy chúng về cuối. Nếu W8 chưa qua freeze gate, main test chưa được chạy; giữ M1 để demo và công bố rõ tiến độ, không lấp thiếu thời gian bằng bỏ evaluation. UI polish và M3 không chặn critical path; research writing vẫn bắt đầu W1.

## 19. MVP and Incremental Delivery Strategy

**[THÊM v1.1 — toàn bộ mục 19]** Đây là chiến lược bàn giao tăng dần cho chính kiến trúc và nghiên cứu đã khóa ở mục 1–18. M0/M1 thu hẹp độ hoàn thiện implementation để có bản chạy sớm; M2 vẫn là đích full đã mô tả. Không thêm cơ chế nghiên cứu hay thay đổi RQ, benchmark và primary contrasts. M3 chỉ là nhóm extension đã được nêu, không phải phần bắt buộc của đề tài.

**Trạng thái hiện tại:** mục này là kế hoạch. Chưa có bằng chứng chạy code, release hay tag của ứng dụng được thẩm định trong lần cập nhật tài liệu này. Vì vậy không đánh dấu M0/M1/M2 DONE thực tế. Tên tag bên dưới là quy ước đề xuất; tag chỉ được tạo sau gate có bằng chứng, không tạo tag vào repository chứa tài liệu để giả định phần mềm đã hoàn tất.

### 19.1. Nguyên tắc vertical slice và bằng chứng DONE

Mỗi milestone phải đi trọn đường **input người dùng → xử lý thật → output có nguồn/trạng thái → trace lưu được → đánh giá đúng mức**. Mọi increment W3/W4/W5 cũng phải giữ đường này chạy được. “Planner 80%, retrieval 70%, UI 80% nhưng chưa nối nhau” không được tính là một milestone gần DONE.

Nhóm tích hợp phần nhỏ ngay khi contract tối thiểu hoạt động; feature mới mặc định off cho tới khi kiểm tra qua cùng entrypoint. Không cần hoàn thiện nội bộ toàn module mới tích hợp. Mỗi tuần người khác owner chạy một demo từ cấu hình release, không dùng mock để chứng minh local LLM đã chạy thật.

Một milestone chỉ được ghi DONE khi có đủ: commit/version; effective config; model/corpus manifest; tập case và kết quả kiểm tra; output/trace; known limitations; hướng dẫn start/restore; người review xác nhận. Chỉ các kiểm tra thuộc mức đó phải hoàn tất, nhưng giới hạn nguồn/quyền truy cập, trạng thái lỗi, chống vượt budget và tính trung thực kết quả không được hoãn.

**M1 là điểm dừng sớm có giá trị nghiên cứu:** đã có hệ thống có thể demo, chạy A/B/C, chấm theo rubric và xuất báo cáo pilot. M1 chưa có toàn bộ bằng chứng ablation/thống kê của M2; báo cáo phải ghi cấp độ và implementation version. Có thể nghiên cứu hoàn chỉnh ở phạm vi MVP mà không được tuyên bố đã hoàn tất toàn bộ protocol main experiment. Không cần C thắng baseline để milestone được nghiệm thu.

### 19.2. M0 — Technical MVP

| Hạng mục | Cam kết M0 |
|---|---|
| Required modules | Một local LLM adapter; ingestion văn bản tối thiểu; chunk/index/retrieve Domain KB; Vanilla RAG A; citation locator/source viewer tối thiểu; token cap; basic trace và terminal error state; một đường vào web chat đơn giản |
| Input/output chính | Input: tệp text được chọn, workspace và câu hỏi. Output: answer với source ID/span hoặc thiếu evidence/lỗi rõ; trace gồm run ID, source/model/config version, retrieval IDs, tokens, thời gian, terminal status |
| Definition of Done | Nhập nguồn mới → index → hỏi → mở được đúng source excerpt; chạy thật offline sau khi tải dependencies; có ít nhất 12 case calibration với kết quả; kiểm tra case đủ/thiếu evidence, tệp lỗi và budget; khởi động lại từ manifest và chạy lại được; giữ LKG |
| Demo scenario | Nhập một đặc tả API nhỏ, hỏi một trường response; mở citation. Hỏi tiếp một thông tin không có trong nguồn để thấy trạng thái thiếu bằng chứng thay vì citation bịa |
| Metrics bắt buộc | Run completion/failure/partial; input/output tokens và LLM calls; retrieval/total E2E latency; RAM/VRAM nếu có; citation locator validity. Chấm tay correctness/faithfulness trên case demo/calibration để phát hiện lỗi, chưa suy ra chất lượng toàn benchmark |
| Git/tag hoặc LKG | Tag đề xuất `m0-technical-mvp-v1` tại commit qua gate; manifest khóa dependencies/model/source snapshot/config A, demo fixtures và report. Giữ bundle/snapshot có checksum nếu chưa có Git release |
| Go/No-Go condition | GO tới B khi slice A chạy lại được, trace khớp output và không có lỗi scope/locator/budget nghiêm trọng chưa xử lý. NO-GO nếu chỉ model chat được nhưng chưa retrieve thật, UI có output mẫu, citation không trỏ nguồn hoặc restore không chạy |
| Nếu trễ thì cắt trước | Hoãn mọi extension/advanced UI/reranker; ingestion chỉ hỗ trợ định dạng text của core cần thiết, báo rõ tệp không hỗ trợ. Không cắt citation, trace, calibration cases hoặc kiểm tra lỗi để ghi M0 DONE |

### 19.3. M1 — Research MVP

| Hạng mục | Cam kết M1 |
|---|---|
| Required modules | Giữ M0/A; thêm Task Decomposition JSON, registry và 3 domain profiles, assignment, task-specific RAG, executor tối thiểu, P-lite, N rules-only bảo thủ, O-lite, synthesis, structured results/citation checks, trace/metrics và một harness chạy/chấm A/B/C |
| Input/output chính | Input: request nhiều nghĩa vụ, workspace snapshot và condition config. Output: task plan, profile assignment, planning evidence/fallback, context selected/dropped, worker results, answer tổng hợp/partial, trace và hàng metrics kèm rubric score |
| Definition of Done | A/B/C chạy end-to-end từ cùng codebase trên cùng model/corpus/hardware; có pilot tối thiểu 15 request development/validation chọn trước ×3 conditions =45 lượt, trải 3 domain và case thiếu evidence/overlap; kết quả đã chấm theo rubric, không chỉ harness rỗng; task/token/latency/failure được xuất; đạt G3 và restore LKG được. Test split vẫn giữ kín; pilot không thay benchmark mục 8 |
| Demo scenario | Review authn/authz, schema và API contract từ một workspace; xem decomposition, P retrieval, 3 profile, O-lite loại duplicate nhưng giữ nguồn chung cần thiết, synthesis có citation. Chạy cùng request bằng A/B/C và mở bảng score/token/latency thực; có thêm case thiếu dữ liệu trả PARTIAL |
| Metrics bắt buộc | Task Coverage, Duplicate Task Rate, Role Assignment, evidence recall trước/sau selection trên cases có gold, Answer Score/SufficientPass, faithfulness chấm người; context/input/output tokens, raw overlap có định nghĩa, LLM calls, E2E latency, RAM/VRAM, failure/partial/retry. Theo từng condition, báo n và N/A đúng; overlap thừa ngữ nghĩa chỉ được claim nếu có nhãn. A không có task plan nên các metric task không áp dụng ghi N/A |
| Git/tag hoặc LKG | `m1-research-mvp-v1` cùng `implementation_profile=m1` và versions P-lite/N-rules/O-lite, presets A/B/C, corpus/Planning KB/model, case list/labels pilot, raw runs/CSV, limitations và restore guide. Giữ nguyên tag M0; W3/W4 có thể giữ checkpoint `w3-b-e2e-v1`, `w4-p-e2e-v1` sau gate |
| Go/No-Go condition | GO tới full core khi A/B/C thực sự chạy và chấm được, lite flags không bị bỏ qua, output/trace/effective config khớp và LKG restore qua. NO-GO nếu C chỉ đổi nhãn của B, P/O là placeholder, chưa chấm một case, hoặc phải sửa code thủ công giữa conditions. Kết quả C kém hơn B là dữ liệu nghiên cứu, không tự nó là NO-GO |
| Nếu trễ thì cắt trước | Giữ P-lite và O-lite; hoãn N semantic/LLM ambiguity batch, MMR/near-duplicate nâng cao, DAG edge cases chưa đạt full, verifier model riêng và UI phụ. Unsupported dependency phải trả trạng thái rõ, không giả vờ xử lý; không chọn lại case chỉ để giấu failure. Dataset/annotation/evaluation tiếp tục là bắt buộc |

**P-lite:** Planning KB nhỏ đã quản lý version, retrieval có relevance gate, tối đa vài planning items có cap, local planner đọc request + items, log fallback không có pattern phù hợp. Không có experience hoặc prompt evolution. Nâng lên P-full hoàn tất mọi kiểm soát ở mục 6.1 trên input dài/không phù hợp và cấu hình đã validation; không thay mục tiêu cơ chế.

**N rules-only:** chuẩn hóa duplicate rõ ràng bằng đối tượng/nghĩa vụ/đầu ra, bảo toàn requirement/constraint/dependency; trường hợp mơ hồ giữ riêng. Code-validity checks luôn có ở mọi condition, kể cả N off. Rules-only vẫn phải có hành vi chuẩn hóa vượt checks ID nếu được khai báo N enabled; không bật flag cho một no-op.

**O-lite:** relevance theo task, exact/span dedup, giữ locator/version, giới hạn token per-call/toàn run và log selected/dropped; giữ evidence chung cần thiết, không global dedup cấm chia sẻ. Chưa đòi hỏi near-duplicate nâng cao, MMR/coverage-aware greedy hoặc redistribution đầy đủ. Vì O-off vốn đã có exact duplicate và hard cap, phải khai báo khác biệt thực của O-lite như span dedup/relevance filtering và đo trace; không đổi tên baseline guard thành contribution mới.

**Executor tối thiểu M1:** thực thi các task độc lập hoặc dependency đơn giản được hỗ trợ theo thứ tự serial; không cần physical parallelism. Schema vẫn giữ dependencies; source/task state và failure propagation không bị xóa. Case DAG chưa xử lý được phải báo `PARTIAL/BLOCKED/UNSUPPORTED_DEPENDENCY` cùng nghĩa vụ chưa hoàn tất. M2 hoàn tất DAG theo đặc tả cũ và kiểm tra các topology đã quy định.

Nếu dừng ở M1, bàn giao tag + demo + pilot report + phạm vi hỗ trợ/chưa hỗ trợ. Giữ title/RQ hiện tại làm mục tiêu đề tài khi P/O vẫn có; mô tả rõ mức thực hiện và câu hỏi chưa đủ bằng chứng trả lời. Không trình bày pilot A/B/C như đã chứng minh primary contrast C/C−P hoặc C/C−O vốn cần ablation M2.

### 19.4. M2 — Core Complete

| Hạng mục | Cam kết M2 |
|---|---|
| Required modules | P/N/O full mục 6; DAG/data dependency và bounded retry/state đầy đủ; Context Controller hoàn chỉnh; A/B/C/C−P/C−N/C−O; benchmark/annotation, freeze, runner/ledger, grading, statistics và failure analysis mục 8–10 |
| Input/output chính | Input: frozen benchmark/splits, source/model/config manifests và condition presets. Output: 6-condition runs, canonical attempt ledger, task/context/answer artifacts, blinded grading, metrics/CI, ablation tables, failure taxonomy và bounded claims |
| Definition of Done | G4 test-ready qua trước test; main evaluation được hoàn tất theo protocol đã khóa (mục tiêu 120 request toàn bộ,60 test×6×3=1.080 test runs), mọi missing/failed attempt reconcile; chấm/CI/ablation/failure analysis xong; report và reproduction package có; M2 release restore qua. `m2-test-ready` ở W8 chưa đủ để gọi M2 DONE |
| Demo scenario | Case có data dependency: worker cha xác định predicate, worker con retrieve sau output đó; xem N giữ nghĩa vụ, O chọn evidence/giữ conflict, targeted retry hoặc partial đúng. Mở bảng 6 conditions và truy một claim trong báo cáo về run/evidence/annotation |
| Metrics bắt buộc | Toàn bộ metric và denominator mục 10, primary contrasts RQ1/RQ2, paired clustered CI, chất lượng/tài nguyên và errors; semantic overlap subset theo protocol; không giảm bộ metric để che các kết quả xấu |
| Git/tag hoặc LKG | `m2-test-ready-v1` khóa code/config trước test; `m2-core-complete-v1` khóa gói kết quả được review. Hai tag tham chiếu cùng frozen runtime commit/config hoặc ghi rõ amendment hợp lệ; giữ mọi tag M0/M1 và raw attempts |
| Go/No-Go condition | GO nghiệm thu khi phương pháp và artifact đủ kiểm chứng; C không bắt buộc thắng. NO-GO cho main test nếu chưa freeze/scope/data integrity; NO-GO cho nhãn Core Complete khi thiếu ablation/chấm/statistics hoặc đã tune bằng test. M3 chỉ bắt đầu sau M2 ổn, restore qua và đã bảo đảm lịch bàn giao |
| Nếu trễ thì cắt trước | Áp ladder mục 19.8 để quay về M1 còn đánh giá được; không gọi bản N-rules/O-lite là M2 full. Ưu tiên hoàn tất dataset/chấm/phân tích; mọi thay đổi quy mô nghiên cứu phải theo amendment trước test, không tự cắt trong lần cập nhật plan này |

### 19.5. M3 — Extensions

| Hạng mục | Cam kết M3 |
|---|---|
| Required modules | Không có extension bắt buộc. Chỉ chọn một extension đã nêu: Experience Library, HERA-style prompt evolution, QLoRA, advanced reranker, advanced UI hoặc mở rộng ngoài core đã được chấp thuận phạm vi; giữ M2 chạy nguyên vẹn |
| Input/output chính | Input: LKG M2, extension config/version, dữ liệu development/train riêng và nguồn lực còn lại. Output: một slice mở rộng runnable, regression report so M2 và kết quả đánh giá theo phạm vi extension; không ghi đè results core |
| Definition of Done | M2 qua gate; extension bật/tắt cùng codebase; test/regression/restore có evidence; extension tạo giá trị quan sát được trong scenario đã chọn; model/prompt/data thay đổi có manifest/protocol riêng. M3 DONE phải nêu extension nào, không có nghĩa đã làm hết danh sách |
| Demo scenario | Ví dụ Experience Library từ development hỗ trợ một request mới, trace chỉ ra insight version; hoặc UI nâng cao mở cùng source/run của M2. Tắt flag quay về M2 và chạy lại demo core |
| Metrics bắt buộc | Regression các metric core liên quan, latency/token/RAM/failure; với extension ảnh hưởng generation/retrieval thì thêm chất lượng và nguồn theo rubric đã đăng ký; UI-only kiểm tra luồng/citation/cancel và thời gian tương tác. Không tạo thêm RQ nghiên cứu bắt buộc cho core |
| Git/tag hoặc LKG | Giữ bất biến `m2-core-complete-v1`; branch đề xuất `codex/ext-<name>`, tag riêng `m3-<extension>-v1` khi qua gate; manifest thể hiện model/data/prompt differences; không tái gắn tag M2 lên extension |
| Go/No-Go condition | GO chỉ khi M2 ổn và có buffer thực, người phụ trách, scope và đánh giá cụ thể. NO-GO khi core/report chưa xong, extension dùng test làm dữ liệu học hoặc không có đường quay về M2 |
| Nếu trễ thì cắt trước | Cắt toàn bộ M3, bàn giao M2. Không kéo trễ main experiment, grading, report hoặc bảo vệ để giữ extension |

### 19.6. Feature flags/config — một codebase, sáu conditions

Chỉ có một implementation cho mỗi module. A đi nhánh single-RAG trong cùng runner; B/C/ablations dùng cùng planner/worker/retrieval/synthesizer với flags. Không sao chép `pipeline_B`, `pipeline_C` thành các codebase khác để chỉnh riêng và làm lệch các biến kiểm soát.

Hai chiều config tách biệt: **condition** mô tả cơ chế bật/tắt; **implementation_profile** mô tả mức trưởng thành lite/full. `C + m1` là C tại milestone M1, không phải kết quả C-full của main experiment. Mọi bảng phải ghi cả hai và version, không gộp số liệu giữa milestones.

| Preset condition | Route | P enabled | N enabled | O enabled | Profile main test |
|---|---|---:|---:|---:|---|
| A | single_rag | false | false | false | m2, shared basic guards |
| B | multi_agent | false | false | false | m2 |
| C | multi_agent | true | true | true | m2: P-full/N-full/O-full |
| C−P | multi_agent | false | true | true | m2 |
| C−N | multi_agent | true | false | true | m2 |
| C−O | multi_agent | true | true | false | m2 |

M0 chỉ hỗ trợ preset A. M1 hỗ trợ A/B/C với P-lite/N-rules/O-lite khi enabled; unsupported presets báo lỗi rõ. M2 hỗ trợ đủ sáu presets, khớp hoàn toàn bảng 9.1. N/O off vẫn có các guards tối thiểu như mục 6, không tắt access control, token caps, schema validation hay citation integrity.

Ví dụ config đề xuất cho C tại M1; các đường dẫn là artifact IDs của manifest, không xác nhận các file thực thi đã tồn tại:

```json
{
  "config_schema": "delivery-v1",
  "implementation_profile": "m1",
  "experiment_id": "m1-pilot-v1",
  "condition": "C",
  "route": "multi_agent",
  "features": {
    "P": {"enabled": true, "implementation": "lite-v1"},
    "N": {"enabled": true, "implementation": "rules-v1"},
    "O": {"enabled": true, "implementation": "lite-v1"}
  },
  "shared_manifest_id": "m1-local-comparison-v1",
  "extensions": {
    "experience": false,
    "prompt_evolution": false,
    "qlora": false,
    "advanced_reranker": false,
    "advanced_ui": false
  }
}
```

`shared_manifest_id` chứa model/checksum, embedding, corpus/chunking, Planning KB, registry/prompts, hardware, sampling, budget/retry/timeouts và seed schedule. Chọn preset trước run rồi resolve config đầy đủ; lưu `effective_config`, `config_hash`, code commit và implementation versions vào trace. Config bất biến suốt run. CLI/batch runner dùng preset, người dùng chat không cần chọn P/N/O.

Validation bắt buộc: preset không khớp flags thì reject; implementation chưa có thì reject, không silent fallback; test chính từ chối profile m1/lite; extensions off cho core experiment; cùng comparison block phải cùng shared manifest trừ đúng fields cơ chế được phép khác. Kiểm tra trace có stage thực chạy hoặc reason bypass, không chỉ thấy config enabled. Thử một fixture đủ điều kiện kích hoạt P/N/O để tránh test flag bật mà module là no-op.

Nếu feature hỏng giữa run thì ghi failure/partial theo protocol; không âm thầm đổi C thành B rồi vẫn ghi condition C. Thử cấu hình fallback là run mới với condition/config/attempt riêng, không thay canonical bằng câu trả lời đẹp hơn.

### 19.7. Rollback policy và Last Known Good Version

LKG là **bản ứng dụng + cấu hình + dữ liệu tương thích + bằng chứng chạy**, không chỉ một commit hay video demo. Sau từng milestone ổn định, release manifest phải ghi: tag/commit; lockfiles/runtime; model/embedding checksums; corpus/index/Planning KB versions; DB schema/snapshot; presets/effective config; smoke cases/expected behavior; raw trace/report; limitations; lệnh start/restore; reviewer/ngày xác nhận.

1. Bắt đầu feature từ LKG trên branch ngắn; giữ version cũ runnable. Tích hợp feature sau flag off và kiểm tra regression slice cũ trước khi bật.
2. Trigger rollback: pipeline không start, mất source/citation/trace, scope leak, budget bypass, state treo, flags sai, data migration không tương thích hoặc regression vượt ngưỡng đã khóa. Một semantic failure đã ghi trong benchmark không tự động là lý do đổi phiên bản giữa test.
3. Dừng promotion/chạy mới trên bản lỗi; lưu logs/attempts và snapshot dữ liệu hiện tại. Nếu toggle về preset đã xác nhận đủ để phục hồi thì tạo run mới có config đúng; nếu không, khởi động bản tag LKG với dữ liệu tương thích trong thư mục/snapshot riêng.
4. Không `reset --hard`, không xóa output, không force-move tag và không ghi đè database mới bằng snapshot cũ mà làm mất dữ liệu. Giữ các records mới cho điều tra; migration phải có kế hoạch tương thích/restore và được thử trên bản sao trước promotion.
5. Chạy lại checklist start → ingest/retrieve → answer → citation → trace → metrics/cancel của LKG. Chỉ khi qua mới cập nhật release đang dùng; branch lỗi tiếp tục sửa riêng, không vá nóng phá phiên bản demo.
6. Sau freeze, lỗi ảnh hưởng main experiment làm dừng experiment để phân loại. Nếu sửa code/config ảnh hưởng kết quả, áp dụng version/amendment và quy tắc canonical/block của mục 9–10; không ghép runs cũ/mới như một condition bất biến. Giữ frozen release để audit và LKG để demo.

Tag bất biến có thể có hậu tố v2 cho lần nghiệm thu mới; không cập nhật nội dung tag v1. Một con trỏ “current LKG” có thể đổi nhưng phải trỏ tới tag bất biến và có lịch sử. Bản backup Markdown v1.0 của kế hoạch chỉ phục vụ đối chiếu tài liệu, không được gọi là LKG phần mềm.

### 19.8. Scope-cut ladder — giữ đường nghiên cứu hoạt động

| Bậc, theo thứ tự | Cắt/hoãn | Phải giữ | Nhãn release/claim sau cắt |
|---|---|---|---|
| 1 | Toàn bộ Extensions: Experience, prompt evolution, QLoRA và mở rộng ngoài core | M0→M1→M2, dataset/evaluation | Không ảnh hưởng mục tiêu M2; M3 không có deadline bắt buộc |
| 2 | Advanced reranker, semantic verifier model riêng, advanced UI | Retriever cơ bản; code verifier/citation checks; chat/source viewer tối thiểu; grading người; tracing | Vẫn đạt M2 nếu đầy đủ P/N/O theo plan; không có module phụ không làm giảm giá trị nghiệm thu |
| 3 | N semantic/LLM ambiguity handling → rules-only | Task obligations/constraints, dependency validity, log normalization; P/O và evaluation | Giữ M1/revised-scope; chưa gắn M2-full; C−N phải ghi đúng N implementation nếu đánh giá phạm vi rút gọn |
| 4 | O advanced MMR/near-duplicate/coverage redistribution → relevance + exact/span dedup + token budget | P-lite, O-lite thật sự chạy; necessary shared evidence; source/version/trace; A/B/C có chấm | Giữ M1; không claim đã kiểm chứng full Context Controller hoặc primary contrast full |
| 5 — chỉ khi bất khả kháng | Xem lại nguồn lực và lịch, khóa bản research MVP cuối cùng; nếu buộc bỏ P hoặc O phải sửa phạm vi đề tài | Dataset, rubric, evaluation và báo cáo trung thực; LKG | Sửa title/RQ/claim và experiment version tương ứng; không gọi đây là thực hiện đầy đủ plan đã khóa |

Không bỏ dataset/evaluation để giữ tính năng phụ, không tune trên test để bù chất lượng và không giảm gold annotation thành nhãn tự chấm không hiệu chuẩn. Mọi quyết định cắt ghi owner, lý do, ngày, module/flag thay đổi, LKG, DoD và claim bị ảnh hưởng. Khối lượng benchmark/statistics mục 8–10 được giữ nguyên ở M2; pilot M1 là evidence riêng, không tự ý thay test60 hoặc 1.080 run bằng số nhỏ hơn rồi gọi main experiment hoàn tất.

### 19.9. Critical Path / Supporting / Extension

“Supporting” là hạ tầng hỗ trợ, không đồng nghĩa optional. Các bản tối thiểu bảo đảm pipeline hợp lệ là điều kiện để milestone qua gate; chỉ mức nâng cao vượt DoD mới được hoãn. Dataset/evaluation vừa có workstream riêng vừa là điều kiện nghiệm thu nghiên cứu.

| Nhóm | Module/công việc | Mốc tối thiểu và full |
|---|---|---|
| Critical Path | Local LLM adapter và calibration; ingestion/index; Vanilla RAG A | End-to-end M0/W2 |
| Critical Path | Task Decomposition; 3 domain profiles/assignment; task-specific RAG; worker; synthesis | B end-to-end W3, tiếp tục dùng ở M1/M2 |
| Critical Path | P retrieval-guided decomposition | Lite W4/M1; full M2 |
| Critical Path | O Context Controller | Lite W5–6/M1; full M2 |
| Critical Path tới M2 | N full; DAG data dependency đầy đủ; C−P/C−N/C−O | N-rules/executor tối thiểu ở M1; full M2, không được bỏ nếu tuyên bố Core Complete |
| Critical Path nghiên cứu | Corpus/Planning KB có version; dataset, split, annotation/rubric; A/B/C harness; freeze; grading/statistics/failure analysis | Bắt đầu W1–2; pilot có điểm ở M1; benchmark/ablation/phân tích full ở M2 |
| Supporting bắt buộc | Registry cấu trúc; schema validation; citation/locator validation; source scope/isolation; token/output reserve; basic error/partial state | Tăng theo chức năng M0→M1; không tắt bằng feature flags |
| Supporting bắt buộc | Trace/metrics export, manifest/ledger, config validation; LKG/rollback và bounded retry/cancel | Basic M0, comparison pilot M1, đầy đủ reproducibility M2 |
| Supporting bắt buộc | Một web chat tối thiểu, history theo luồng đã có, source viewer, status/error dễ hiểu, reproduction guide | Đủ demo end-to-end; polish không chặn research |
| Extension | Experience Library, HERA-style prompt evolution, QLoRA | M3 sau M2 ổn, protocol/data riêng |
| Extension | Advanced reranker, semantic verifier nâng cao, advanced UI hoặc các tiện ích ngoài DoD core | Không critical path; không thay model/retriever riêng cho C trong core experiment |

### 19.10. Checklist “Nếu hôm nay dự án dừng thì phiên bản gần nhất demo được là gì?”

Mỗi buổi review tuần điền checklist bằng evidence, không bằng phần trăm code. Chọn **mức cao nhất đã qua DoD và restore**, không phải branch mới nhất hoặc milestone dự định đạt.

- [ ] Có tag/commit LKG hoặc bundle checksum cụ thể và reviewer xác nhận.
- [ ] Có runtime/dependency/model/index/DB snapshot tương thích; khởi động từ hướng dẫn mà không sửa code thủ công.
- [ ] Có thể chạy offline với local LLM thật sau setup; không dùng output mock thay demo live.
- [ ] Có một request đi từ nhập dữ liệu đến answer/citation/trace; source excerpt khớp đúng phiên bản.
- [ ] Có case thiếu evidence/lỗi/cancel đi tới trạng thái terminal rõ; không treo pipeline hoặc báo thành công giả.
- [ ] Nếu khai báo M1 trở lên: A/B/C chạy cùng codebase/model/corpus/hardware, P/O lite/full đúng manifest; có pilot raw outputs và rubric scores thật.
- [ ] Nếu khai báo M2: full P/N/O + DAG + sáu conditions, freeze/test labels đúng, benchmark/chấm/CI/failure analysis hoàn tất và ledger reconcile.
- [ ] Có thể chỉ ra dữ liệu/metric nào đã đo, metric nào N/A/chưa đo và phần nào chưa hỗ trợ; không đánh đồng citation validity với semantic correctness.
- [ ] Một người khác đã thử restore và chạy lại ít nhất case bình thường + case thiếu thông tin từ LKG.
- [ ] Report/demo script ghi rõ milestone/implementation version, known limitations, kết luận được phép và next milestone; không claim novelty vượt nguồn hay coi overlap luôn xấu.

| Evidence cao nhất hiện có | Câu trả lời phải ghi khi dự án dừng |
|---|---|
| Chưa có M0 qua gate | “Chưa có technical MVP end-to-end được xác nhận”; chỉ có thiết kế/module rời, không gọi demo hoàn chỉnh |
| M0 qua gate | “Demo được local Vanilla RAG với ingestion/citation/basic trace”; chưa đủ research MVP đa agent |
| W3/W4 đã qua gate, M1 chưa qua | “Demo được increment B hoặc P trên LKG đã ghi”; không nâng nhãn thành M1 chỉ vì có nhiều agent |
| M1 qua gate | “Demo và đánh giá được Research MVP A/B/C với P-lite/N-rules/O-lite”; có pilot report, chưa claim full ablation/main results |
| M2 qua gate | “Demo và bảo vệ được core nghiên cứu đầy đủ, kèm benchmark/ablation/statistics/failure analysis” |
| Đang phát triển M3 | “LKG M2 vẫn là bản bàn giao”; chỉ trình bày extension nếu đã qua gate riêng |

Mẫu chốt một dòng: `Ngày review | milestone thực đạt | tag/commit + manifest | demo case IDs | raw trace/report | giới hạn | reviewer | rollback đã thử`. **Ở lần cập nhật tài liệu này: phiên bản ứng dụng demo được gần nhất = CHƯA XÁC MINH**, vì chưa audit code/runs/releases; plan v1.1 không phải bằng chứng rằng M0 đã chạy.

### 19.11. Phương pháp nghiên cứu tiếp tục có hiệu lực

Giữ nguyên freeze trước test, split/chống leakage, same model/corpus/hardware và shared settings giữa conditions, canonical attempts và failure denominators. Giữ RQ1/RQ2 cùng primary contrasts mục 9–10, không thay bằng chỉ A/B/C để dễ hoàn tất M1. Không nâng claim novelty, không dùng raw overlap như metric lỗi ngữ nghĩa, không coi citation đúng ID là câu trả lời đúng. Mọi test/failure và dữ liệu âm phải được giữ; thí nghiệm M1 và M2 có version riêng và không gộp tùy tiện.

### 19.12. Nhật ký cập nhật có kiểm soát

| Vị trí | Thay đổi v1.1 | Phần được giữ |
|---|---|---|
| Đầu tài liệu, 1.1 | Version, nguồn snapshot mới, change markers, liên hệ core với M2 | Tên đề tài và scope kiến trúc |
| 12.2 | Thay timeline thành W2 M0, W3 B, W4 P, W5–6 M1, W7+ M2 | 12 tuần, nhân lực, research workstream và gates freeze |
| 12.3 | Ghi staging lite/full cho ticket | Toàn bộ ticket/owner/DoD full |
| 13.2 | Gắn G1–G5 với delivery gates/LKG | Nguyên tắc chất lượng, freeze, evidence và không yêu cầu kết quả dương |
| 14 | Scope-cut ladder có O-lite và bảo vệ dataset/evaluation | Risk table, phạm vi nghiên cứu và amendment trước test |
| 19 mới | M0–M3, DoD/demo/metrics/LKG, flags, rollback, module classification, stop-today checklist | Không thay thuật toán, RQ, A/B/C/ablation, benchmark, metrics, tài liệu tham khảo ở các mục trước |

