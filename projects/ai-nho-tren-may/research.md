# Vì sao mô hình AI nhỏ chạy trên máy đang quay trở lại

## Tóm tắt 5 dòng

1. "AI chạy trên máy" không phải mới — mô hình BERT-độ nhỏ (100M–1B tham số) từng chạy trên điện thoại từ 2018–2020, rồi bị khuất phục bởi kỷ nguyên LLM khổng lồ dựa vào cloud (GPT-3, GPT-4); giờ nó trở lại dưới dạng Small Language Model (SLM) thế hệ mới.
2. Ba động lực hội tụ: kỹ thuật nén mô hình (quantization, knowledge distillation, kiến trúc MoE/PLE) cho phép mô hình 1–4B tham số chạy mượt trên điện thoại; phần cứng có NPU chuyên biệt (Apple Neural Engine, Snapdragon X 45 TOPS, chuẩn Copilot+ PC ≥40 TOPS); và áp lực chi phí/riêng tư của cloud AI.
3. Bằng chứng rõ nhất là sản phẩm thật: Apple dùng mô hình ~3B chạy on-device trong Apple Intelligence (nén 2-bit QAT), Google ra Gemma 3n "hiệu dụng" chỉ 2B–4B tham số, Microsoft có dòng Phi, Meta có Llama 3.2 1B/3B cho thiết bị di động.
4. MIT Technology Review xếp small language models vào danh sách 10 Breakthrough Technologies 2025; một nghiên cứu ACL 2025 rà soát 68 SLM cho thấy điểm benchmark của SLM tăng 12,5% từ 3/2023 đến 9/2024 — nhanh hơn cả LLaMA-7B.
5. Nhưng giới hạn vẫn thật: SLM yếu ở reasoning phức tạp, context dài, đa nhiệm; và chính Apple — hãng tiên phong on-device — cũng phải dựng tầng hybrid (on-device → Private Cloud Compute → Gemini của Google), cho thấy cloud chưa bị thay thế.

## 7–10 luận điểm chính

**1. Đây là sự "trở lại", không phải sự ra đời.** Timeline các mô hình sub-4B chạy trên thiết bị bắt đầu từ 2018 với MobileBERT, DistilBERT, TinyBERT, T5-small — rồi bùng nổ mạnh từ 2023 trở đi (Llama 3.2, SmolLM, Ministral, Phi, Gemma). Nguồn: bài khảo sát *Edge-First Language Model Inference* (arXiv 2505.16508) có biểu đồ thời gian minh họa rõ. *Suy luận của tôi: giai đoạn 2020–2023, cuộc đua "scale là mọi thứ" (trích phát biểu của Noam Brown, OpenAI, tại TEDAI 10/2024 trong MIT Technology Review) đã đẩy trung tâm trọng lượng về data center, và nay đường cong lợi nhuận biên của mô hình lớn chững lại nên xu hướng đảo chiều.*

**2. Giới nghiên cứu công nhận SLM là xu hướng, không phải phong trào marketing.** MIT Technology Review (3/1/2025) chọn "Small language models" là 1 trong 10 Breakthrough Technologies 2025, với lập luận: với các tác vụ cụ thể, mô hình nhỏ huấn luyện trên dữ liệu tập trung "hoạt động tốt bằng甚至 tốt hơn" mô hình lớn. TechTarget (11/3/2025) định nghĩa SLM thường dưới ~30 tỷ tham số, huấn luyện trên dữ liệu curated thay vì scrape cả internet.

**3. Năng lực SLM đang tăng nhanh — số liệu cụ thể.** Nghiên cứu ACL 2025 (*Demystifying Small Language Models for Edge Deployment*, khảo sát 68 SLM trong khoảng 100M–5B tham số): từ tháng 3/2023 đến tháng 9/2024, điểm SLM cải thiện trung bình 12,5%, vượt mức 7,5% của series LLaMA-7B cùng kỳ; SLM đã vượt cả LLaMA-7B v1 trên các benchmark nhận thức thông thường. Ví dụ điển hình: Phi-3-mini (3,8B) đạt 69% MMLU, cạnh tranh với Mixtral 8x7B và GPT-3.5 (theo *On-Device Language Models: A Comprehensive Review*, arXiv 2409.00088).

**4. "Kỹ thuật nén" là chất xúc tác khiến làn sóng này khác 2019.** Ba biện pháp chính: quantization (ưu thế weight 4-bit giảm dung lượng ~68,66%, đưa Llama 3.2 3B chạy được trên điện thoại Android phổ thông — arXiv 2512.06490), knowledge distillation (học từ mô hình thầy lớn), và kiến trúc tiết kiệm tham số (MoE sparse, Per-Layer Embedding caching, MatFormer). Google Gemma 3n minh họa rõ nhất: tổng trên 5B tham số nhưng chỉ nạp hiệu quả 1,91B vào bộ nhớ nhờ PLE caching và parameter skipping (tài liệu chính thức của Google AI for Developers). Apple dùng 2-bit quantization-aware training + KV-cache sharing cho mô hình ~3B của họ (Tech Report Apple Intelligence 2025, arXiv 2507.13575).

**5. Phần cứng thiết bị đã đủ mạnh — đây là điều kiện cần.** Chuẩn Copilot+ PC của Microsoft đòi hỏi NPU ≥40 TOPS, RAM ≥16GB, SSD ≥256GB (Microsoft Learn; Qualcomm công bố Snapdragon X Elite/Plus đạt 45 TOPS). IDC (trong white paper được Intel tài trợ) gọi đây là "Next-Generation AI PC" và dự báo nhiều khối lượng công việc AI sẽ chuyển từ data center xuống edge để scale. Điện thoại flagship cũng có Neural Engine tương đương về mặt khái niệm. *Suy luận của tôi: cột mốc 40 TOPS giống như "ngưỡng đủ" để nhà phát triển yên tâm nhúng LLM vào app, tương tự cách chuẩn WebAssembly hay GPU compute từng tạo bước ngoặt.*

**6. Bốn động lực thực dụng (không phải cảm hứng):** độ trễ (cloud round-trip 100–500ms vs xử lý cục bộ <10–20ms theo bảng so sánh trong arXiv 2507.11545 — *lưu ý: đây là preprint, số liệu mang tính ước lượng), chi phí (API ~5–15 USD/1M token vs điện năng cục bộ gần bằng 0), quyền riêng tư (dữ liệu không rời máy), và khả năng chạy ngoại tuyến. Microsoft cũng nhấn mạnh cùng bộ lý do này cho SLM (Microsoft Community Hub, 10/2025).

**7. Quy mô thị trường cho thấy tiền đang chảy theo.** Review arXiv 2409.00088 dẫn số liệu Market.us: thị trường edge AI từ 15,2 tỷ USD (2022) lên dự báo 143,6 tỷ USD (2032), CAGR 25,9%. *Mâu thuẫn cần ghi nhận:* một nguồn khác (arXiv 2507.11545) lại đưa con số 9 tỷ USD (2025) → 49,6 tỷ USD (2030), CAGR 38,5%. Hai ước lượng khác nhau đáng kể về cả quy mô lẫn tốc độ — nếu dùng trong video nên trích một nguồn và nói rõ "theo ước tính của..." thay vì khẳng định chắc chắn.

**8. Sản phẩm thật đã lên kệ, không chỉ paper.** Apple Intelligence: mô hình ~3B on-device + framework Foundation Models cho developer gọi trực tiếp model on-device từ Swift, ra mắt cùng iOS 26/iPadOS 26/macOS 26 (Apple Newsroom, 29/9/2025); báo cáo kỹ thuật 2025 của Apple cho biết mô hình on-device beat Qwen-2.5-3B trên mọi ngôn ngữ đo lường và cạnh tranh với Qwen-3-4B/Gemma-3-4B ở tiếng Anh. Google: Gemma 3n (E2B/E4B) optimized cho điện thoại/laptop/tablet, hỗ trợ đa phương thức (text, ảnh, video, audio), huấn luyện trên hơn 140 ngôn ngữ (tài liệu Google AI for Developers). Meta: Llama 3.2 1B/3B cho edge/mobile. Microsoft: dòng Phi (Phi-3-mini, Phi-4-mini 3,8B, license MIT).

**9. Nhưng "nhỏ thay thế lớn" chỉ đúng một phần — bằng chứng từ chính hãng lớn nhất.** Apple (WWDC 6/2026) công bố thế hệ AFM thứ 3 gồm 5 mô hình: 2 model on-device (AFM 3 Core ~3B và AFM 3 Core Advanced ~20B chạy bằng cách lưu toàn bộ weights trong flash storage, chỉ nạp 1–4B "expert" params vào RAM mỗi prompt — kỹ thuật gọi là Instruction-Following Pruning) + 3 model server trên Private Cloud Compute; đồng thời hợp tác với Google (train trên TPU của Google, Siri dùng cả model Google Gemini cho tác vụ nặng — Ars Technica 28/5/2026 và TheNextWeb 9/6/2026). *Suy luận của tôi: Apple đang đi theo kiến trúc 3 tầng (on-device → cloud riêng → cloud đối tác), tức là "AI trên máy" là lớp đầu tiên và rẻ nhất trong chuỗi, không phải sự thay thế cloud.*

**10. Lợi điểm yếu cố hữu của SLM mà người xem cần biết.** Benchmark dài: mô hình nhỏ (Qwen2.5-0.5B) sụt mạnh khi context dài, trong khi Qwen2.5-3B giữ ổn định; hiện tượng "lost in the Middle" cũng xuất hiện ở model nhỏ (arXiv 2409.15790). Nói rộng hơn, nghiên cứu 2026 về benchmark saturation (arXiv 2602.16763) cho thấy gần một nửa trong 60 benchmark ngôn ngữ bị bão hòa — nên mọi tuyên bố "mô hình nhỏ đạt X% của mô hình lớn" đều cần hoài nghi, vì chính benchmark đang mất sức phân biệt.

## Góc khai thác cho video

- **Góc lịch sử:** "Lịch sử lặp lại" — từ thời DistilBERT chạy trên điện thoại (2018), AI bị cloud hóa bởi cuộc đua scale, rồi quay về thiết bị; kể theo trục thời gian để thấy bức tranh lớn hơn tin tức tuần này.
- **Góc kỹ thuật "trong bụng điện thoại":** giải thích ba bí thuật nén (quantization, distillation, sparse/MoE + flash-storing 20B params của Apple) bằng hình ảnh trực quan — tại sao 4-bit lại đủ dùng và mô hình 20B lại chạy được trong RAM 8GB.
- **Góc thương chiến & quyền riêng tư:** vì sao Apple, Google, Microsoft, Meta đều có dòng model nhỏ riêng; on-device mang lại privacy thế nào và vì sao Apple vẫn phải nhờ Google Gemini — AI trên máy là chiến lược kinh doanh, không chỉ kỹ thuật.

## Điều gì gây tranh cãi / dễ hiểu sai

- **"Mô hình nhỏ bằng model lớn" là hiểu sai.** Các benchmark mà SLM "ngang ngửa" thường là tác vụ hẹp (tổng hợp, tóm tắt, trích xuất). reasoning sâu, toán, code phức tạp vẫn thuộc cloud. Apple nói rõ mô hình 3B của họ "không phải chatbot kiến thức thế giới chung" (tech report 2025).
- **Con số thị trường edge AI mâu thuẫn giữa các nguồn** (xem luận điểm 7) — không nên trình bày một con số như sự thật tuyệt đối.
- **"Riêng tư tuyệt đối" khi chạy on-device cũng là phóng đại.** IAPP (7/4/2025) cảnh báo: thiết bị phân tán mở rộng bề mặt tấn công, và các biện pháp bảo mật trên thiết bị có thể làm giảm hiệu năng/trải nghiệm. Local inference cũng không đảm bảo cả app local (logging, retrieval vẫn có thể gửi dữ liệu đi).
- **Hệ quả phụ của quantization:** tài liệu chính thức của Google thừa nhận quantized GGUF "thường làm giảm chất lượng output" — đánh đổi giữa chất lượng và chi phí tính toán là có thật.
- **Thuật ngữ "nhỏ" không có ngưỡng chuẩn:** một survey giới hạn ≤5B, TechTarget nói <30B — cần định nghĩa rõ khi lên sóng.
- *Cảnh báo nguồn:* một số bài viết 2026 về "Apple distill Gemini" (perplexityaimagazine, plainenglish) là blog chất lượng không cao; số liệu cốt lõi ở luận điểm 9 đã được đối chiếu bằng Ars Technica, TheNextWeb và tài liệu chính thức của Apple.

## Giới hạn

- Chưa có số liệu đo thực tế kiểu "mỗi giây trả lời trên iPhone/Android tầm trung" từ nguồn độc lập quy mô lớn; các so sánh latency (100–500ms cloud vs <10–20ms local) đến từ preprint và bảng tổng hợp, không phải đo đạc chuẩn hóa.
- Số liệu market size dựa trên báo cáo thương mại (Market.us) dẫn lại qua paper, không tiếp cận được báo cáo gốc.
- Nội dung về AFM 3 / Siri-Gemini (2026) dựa vào tin báo chí và bài kỹ thuật gián tiếp; chưa có tech report đầy đủ cho thế hệ thứ 3 như năm 2025.

## Nguồn

- [Small language models: 10 Breakthrough Technologies 2025 — MIT Technology Review](https://www.technologyreview.com/2025/01/03/1108800/small-language-models-ai-breakthrough-technologies-2025) — truy cập 2026-10-20
- [Why small language models are on the rise — TechTarget](https://www.techtarget.com/ai/tip/Why-small-language-models-are-on-the-rise) — truy cập 2026-10-20
- [Demystifying Small Language Models for Edge Deployment — ACL 2025](https://aclanthology.org/2025.acl-long.718.pdf) — truy cập 2026-10-20
- [Edge-First Language Model Inference: Models, Metrics, and Tradeoffs — arXiv](https://arxiv.org/pdf/2505.16508) — truy cập 2026-10-20
- [On-Device Language Models: A Comprehensive Review — arXiv](https://arxiv.org/html/2409.00088v1) — truy cập 2026-10-20
- [Demystifying/Analysis of SLMs (định nghĩa 5B, "lost in the middle") — arXiv](https://arxiv.org/pdf/2409.15790v2) — truy cập 2026-10-20
- [Apple Intelligence Foundation Language Models: Tech Report 2025 — Apple/arXiv](https://arxiv.org/abs/2507.13575) — truy cập 2026-10-20
- [Updates to Apple's On-Device and Server Foundation Language Models — Apple ML Research](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates) — truy cập 2026-10-20
- [Apple's Foundation Models framework unlocks new app experiences — Apple Newsroom](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) — truy cập 2026-10-20
- [Gemma 3n model overview — Google AI for Developers](https://ai.google.dev/gemma/docs/gemma-3n) — truy cập 2026-10-20
- [Understanding Small Language Models — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/understanding-small-language-modes/4462827) — truy cập 2026-10-20
- [Copilot+ PCs developer guide — Microsoft Learn](https://learn.microsoft.com/en-us/windows/ai/npu-devices/) — truy cập 2026-10-20
- [What on Earth is a Copilot+ PC? — Qualcomm](https://www.qualcomm.com/news/onq/2024/06/what-on-earth-is-a-copilot-plus-pc) — truy cập 2026-10-20
- [Optimizing LLMs Using Quantization For Mobile Execution (giảm 68,66% dung lượng Llama 3.2 3B) — arXiv](https://arxiv.org/html/2512.06490v1) — truy cập 2026-10-20
- [The AI Shadow War: SaaS vs. Edge Computing Architectures — arXiv](https://arxiv.org/html/2507.11545v1) — truy cập 2026-10-20
- [EDGE AI: Paving the Way for Intelligent, Resilient... (IDC/Intel white paper)](https://cdrdv2-public.intel.com/867305/IDC%20Edge%20AI%20white%20paper.pdf) — truy cập 2026-10-20
- [Towards a tailored approach for privacy, trustworthiness in Edge AI — IAPP](https://www.iapp.org/news/a/towards-a-tailored-approach-for-privacy-trustworthiness-in-edge-ai) — truy cập 2026-10-20
- [When AI Benchmarks Plateau: A Systematic Study of Benchmark Saturation — arXiv](https://arxiv.org/abs/2602.16763) — truy cập 2026-10-20
- [Apple working to cram massive Gemini model into iPhone to power new Siri — Ars Technica](https://arstechnica.com/ai/2026/05/apple-reportedly-trying-to-distill-googles-multi-trillion-parameter-gemini-ai-to-run-on-iphone) — truy cập 2026-10-20
- [Apple's real AI story isn't Siri: it's a 20-billion-parameter model that runs from your iPhone's flash — TheNextWeb](https://thenextweb.com/news/apple-third-generation-foundation-models-afm) — truy cập 2026-10-20
