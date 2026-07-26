[English](../../README.md) | [简体中文](../zh-CN/README.md) | [繁體中文](../zh-TW/README.md) | [日本語](../ja/README.md) | [한국어](../ko/README.md) | [Español](../es/README.md) | [Português (BR)](../pt-BR/README.md) | [Deutsch](../de/README.md) | [Français](../fr/README.md) | [Русский](../ru/README.md) | [Türkçe](../tr/README.md) | **Tiếng Việt** | [हिन्दी](../hi/README.md)

# burnrate

**Tìm ra thứ thực sự đang đốt token của tác nhân lập trình của bạn — đo từ chính các phiên làm việc của bạn, không phải một con số phần trăm quảng cáo.**

Mọi skill tiết kiệm token đều hứa hẹn một con số. `tiết kiệm 65%`. `hóa đơn thấp hơn ~31%`. Những con số đó đến từ phiên làm việc của người khác, với tệp và thói quen của họ. Chúng không phải của bạn, và bạn không thể kiểm chứng.

Vậy hãy kiểm chứng của chính bạn. Một lệnh, không cài đặt, không API key, không cần mạng:

```bash
python burnrate.py --all
```

---

## Điều không ai đo

Đây là dữ liệu thật từ 348 phiên — 36.000 lượt mô hình, 8,8 tỷ token:

| | token thô | tỷ lệ | tỷ lệ theo trọng số chi phí |
|---|---:|---:|---:|
| **ngữ cảnh gửi lại mỗi lượt** (cache read) | 8.310.254.792 | **94,2%** | 49,6% |
| ngữ cảnh được ghi (cache write) | 446.493.285 | 5,1% | 33,3% |
| **đầu ra — thứ tác nhân viết ra** | 54.477.459 | **0,6%** | 16,3% |
| đầu vào (không cache) | 13.730.167 | 0,2% | 0,8% |

**Ngữ cảnh: 99,2% token thô, 82,9% theo trọng số chi phí. Đầu ra: 0,6% thô, 16,3% có trọng số.**

Phiên trung vị gửi lại lượng ngữ cảnh gấp **109 lần** những gì nó viết ra. Trong 348 phiên, chỉ **5 phiên** viết nhiều hơn đọc lại.

Mọi skill tiết kiệm token bằng cách rút ngắn câu trả lời, bỏ mạo từ, hay nói kiểu "người tiền sử" đều đang tối ưu cái **0,6%** đó. Ngay cả khi tính đến giá cao hơn của token đầu ra, nó vẫn nhắm vào mục nhỏ nhất trong bốn mục — trong khi chính chỉ dẫn của nó lại được thêm vào ngữ cảnh gửi lại mỗi lượt, mãi mãi.

Đó là lý do phần tiết kiệm chẳng bao giờ thực sự xuất hiện.

*(Cả hai tỷ lệ đều được hiển thị vì chúng kể hai câu chuyện khác nhau. Tỷ lệ thô là thứ lấp đầy cửa sổ ngữ cảnh của bạn; tỷ lệ có trọng số dùng các hệ số tính phí đã công bố — cache write 1,25×, cache read 0,10×, đầu ra gấp 5× đầu vào. Chỉ trích dẫn con số có lợi cho mình chính là vấn đề, không phải giải pháp.)*

## Chạy trên số liệu của chính bạn

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+, chỉ dùng thư viện chuẩn — không `pip install`, không Node, không trình cài đặt shell, không `curl | bash`. Hoạt động như nhau trên Windows, macOS và Linux.

Nó đọc các bản ghi phiên đã có sẵn trên đĩa của bạn (`~/.claude/projects/**/*.jsonl`) và in ra:

- phân bổ token thô và có trọng số của bạn
- công cụ nào đưa nhiều nội dung nhất vào ngữ cảnh, và kích thước kết quả trung bình
- những tệp nào bạn đọc đi đọc lại
- những tệp nào đủ lớn để một mình chi phối cả một phiên
- tải trọng ảnh và tệp nhị phân, được đếm riêng và trung thực

```
  [HIGH] 94 tệp được đọc từ 5 lần trở lên
      Đọc lại cùng những tệp không thay đổi tốn khoảng 2,4 triệu token
      ngoài lần đọc đầu tiên (ước tính). Tệ nhất:
      project-notes.md (107 lần).
      -> Chúng bị đọc lại vì nội dung không trụ được trong ngữ cảnh.

  [HIGH] Read tạo ra 50% tất cả những gì quay lại ngữ cảnh
      3.100 lệnh gọi trả về ~4,5 triệu token; trung bình 1.400 token mỗi
      lệnh gọi, kết quả đơn lẻ lớn nhất ~16.800 token.
      -> Hãy đọc bằng offset/limit thay vì cả tệp.
```

## Những gì được nạp trước khi bạn gõ bất cứ điều gì

```bash
python burnrate.py --startup
```

Ngữ cảnh khởi động được tính phí ở **mỗi lượt của mỗi phiên**, nên đây là thông tin có đòn bẩy lớn nhất. Kết quả thật:

```
-- ĐO ĐƯỢC (lượt tính phí đầu tiên của mỗi phiên) ---------------
  ngữ cảnh khởi động (trung vị)   60.057 token   trên 310 phiên
  Nó được gửi lại dưới dạng cache_read ở TẤT CẢ các lượt sau.

-- QUY GÁN (quét cấu hình của bạn, ước tính) --------------------
  mô tả skill                           12.998  105 skill
  CLAUDE.md (người dùng)                 3.674
  chỉ mục bộ nhớ (MEMORY.md)             2.718  giới hạn 200 dòng / 25KB
  mô tả tác nhân phụ                     1.258  18 tác nhân
  tổng quy gán được                     20.648

  phần dư không quy gán được            39.409  system prompt + schema công cụ
  phần của bạn                            34,4%  là phần bạn có thể cắt
```

Ba điều khiến nó khác với một công cụ ước lượng tệp cấu hình:

- Con số **đo được** là chính xác — nó đến từ trường `usage`, không phải từ việc đếm chữ.
- **Phần dư** được báo cáo thay vì giấu đi. Hai phần ba chi phí khởi động đó là system prompt và schema công cụ, thứ sẽ không đổi dù bạn sửa tệp của mình bao nhiêu đi nữa. Nói cho bạn biết điều này giúp bạn khỏi tối ưu một con số bạn không thể lay chuyển.
- Với skill và tác nhân, **chỉ frontmatter được tính**. Phần thân nạp theo yêu cầu, nên việc đếm cả tệp skill — như các công cụ quét thư mục cấu hình thường làm — sẽ thổi phồng chi phí khởi động lên nhiều lần.

Bất ngờ thường gặp: **những skill đã cài nhưng không dùng còn nặng hơn `CLAUDE.md`.** Mô tả của mỗi skill được nạp mỗi lượt dù bạn có gọi nó hay không, nên `--startup` sẽ chỉ đích danh những cái nặng nhất.

## Chứng minh phần tiết kiệm của chính bạn

```bash
python burnrate.py --snapshot before
#  ... thay đổi điều gì đó ...
python burnrate.py --compare before
```

`--compare` báo cáo **trung bình mỗi lượt**, nên một tuần bận rộn hơn không thể giả dạng thành sự thụt lùi:

```
                                            trước    bây giờ   thay đổi
  cache write (ngữ cảnh mới)                  8.6K       5.9K    -31,7%
  cache read (gửi lại mỗi lượt)              213.3K     219.5K      2,9%
  đầu ra (thứ tác nhân đã viết)                1.4K       1.4K      1,3%

  theo trọng số chi phí, mỗi lượt             39.1K      36.4K     -6,9%

  Đây là thay đổi bạn đo được. Nó không phải khẳng định về của ai khác.
```

## Cài đặt như một skill

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Sau khi cài, nó làm ba việc: đo trước khi khuyến nghị; áp dụng kỷ luật ngữ cảnh nhắm vào 83–99% đắt đỏ thay vì 0,6% rẻ tiền; rồi đo lại để cải thiện là một sự thật. Sổ tay cắt giảm đầy đủ — sắp xếp theo mức tác động, kèm cái giá của từng lần cắt — nằm ở [`references/cuts.md`](../../plugins/burnrate/skills/burnrate/references/cuts.md).

## Những gì nó sẽ không làm

- **Không khiến tác nhân của bạn nói năng kỳ quặc.** Kiểu nói điện tín cắt được một phần nhỏ hóa đơn nhưng làm kết quả khó rà soát hơn.
- **Không đưa cho bạn một con số trung bình.** Chỉ những con số bạn đo được.
- **Không giấu chi phí của chính nó.** Khi được gọi, tệp skill này cũng vào ngữ cảnh. Trong các phiên ngắn, chi phí đó có thể vượt phần nó tiết kiệm — và `--compare` sẽ trung thực cho bạn thấy.
- **Không đánh đổi tính đúng đắn lấy token.** Sự cô đọng chỉ áp dụng cho thứ được truyền đi, không bao giờ cho lập luận, kiểm thử, hay nguyên văn mã nguồn và lỗi.

## Giới hạn đã biết

- Tổng token đến từ trường `usage` và là chính xác. Khối lượng kết quả công cụ được quy đổi ở mức ~4 ký tự/token và được ghi rõ là ước tính ở mọi nơi nó xuất hiện.
- Ảnh và PDF được tính phí theo kích thước, không theo ký tự. Chúng được đếm riêng và không bao giờ quy đổi thành số token.
- Trọng số chi phí dùng các tỷ lệ đã công bố giữa các loại token, không phải giá theo từng mô hình — nên cột có trọng số là một tỷ lệ, không phải số tiền.
- Các gói thuê bao có thể tính trọng số mức dùng khác với giá API. Chính vì vậy cả tỷ lệ thô và có trọng số đều được báo cáo; không cái nào được trình bày như một hóa đơn.
- Chỉ thấy được bản ghi phiên cục bộ. Công việc làm trên máy khác hoặc trong trình duyệt không được tính.
- Dữ liệu ở trên là 348 phiên của một người dùng cường độ cao. Đó là bằng chứng, không phải quy luật phổ quát — và đó chính là điểm mấu chốt. Hãy chạy trên dữ liệu của bạn.

## Giấy phép

MIT
