[English](../../README.md) | [简体中文](../zh-CN/README.md) | [繁體中文](../zh-TW/README.md) | [日本語](../ja/README.md) | [한국어](../ko/README.md) | [Español](../es/README.md) | [Português (BR)](../pt-BR/README.md) | [Deutsch](../de/README.md) | [Français](../fr/README.md) | [Русский](../ru/README.md) | **Türkçe** | [Tiếng Việt](../vi/README.md) | [हिन्दी](../hi/README.md)

# burnrate

**Kodlama ajanınızın token'larını gerçekte neyin yaktığını öğrenin — pazarlama yüzdesiyle değil, kendi oturumlarınızdan ölçülmüş verilerle.**

Her token tasarrufu skill'i size bir sayı vaat eder. `%65 tasarruf`. `~%31 daha düşük fatura`. Bu sayılar başkasının oturumlarından, başkasının dosyalarından ve alışkanlıklarından çıktı. Sizin değiller ve doğrulayamazsınız.

O halde kendinizinkini doğrulayın. Tek komut, kurulum yok, API anahtarı yok, ağ bağlantısı yok:

```bash
python burnrate.py --all
```

---

## Kimsenin ölçmediği şey

İşte 348 oturumluk gerçek bir veri kümesi — 36.000 model turu, 8,8 milyar token:

| | ham token | pay | maliyet ağırlıklı pay |
|---|---:|---:|---:|
| **her turda yeniden gönderilen bağlam** (cache read) | 8.310.254.792 | **%94,2** | %49,6 |
| yazılan bağlam (cache write) | 446.493.285 | %5,1 | %33,3 |
| **çıktı — ajanın yazdığı şey** | 54.477.459 | **%0,6** | %16,3 |
| girdi (önbelleksiz) | 13.730.167 | %0,2 | %0,8 |

**Bağlam: ham token'ların %99,2'si, maliyet ağırlıklı %82,9'u. Çıktı: ham %0,6, ağırlıklı %16,3.**

Medyan oturum, yazdığından **109 kat fazla** bağlam yeniden gönderdi. 348 oturumdan yalnızca **5'i** yeniden okuduğundan fazlasını yazdı.

Yanıtları kısaltarak, artikelleri atarak ya da mağara adamı gibi konuşarak token tasarrufu yapan her skill, işte bu **%0,6'yı** optimize ediyor. Çıktı token'larının daha yüksek fiyatı hesaba katılsa bile, dört kalemin en küçüğünü hedefliyor — üstelik kendi talimatlarını, her turda yeniden gönderilen bağlama ekleyerek. Sonsuza dek.

Tasarrufun bir türlü ortaya çıkmamasının nedeni bu.

*(Her iki pay da gösteriliyor çünkü farklı hikâyeler anlatıyorlar. Ham pay, bağlam pencerenizi dolduran şeydir; ağırlıklı pay ise yayımlanmış faturalama oranlarını kullanır — cache write 1,25×, cache read 0,10×, çıktı girdinin 5 katı. Yalnızca işinize geleni alıntılamak sorunun ta kendisidir, çözümü değil.)*

## Kendi rakamlarınızla çalıştırın

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+, yalnızca standart kütüphane — `pip install` yok, Node yok, shell kurulum betiği yok, `curl | bash` yok. Windows, macOS ve Linux'ta aynı şekilde çalışır.

Diskinizde zaten bulunan oturum kayıtlarını (`~/.claude/projects/**/*.jsonl`) okur ve şunları yazdırır:

- ham ve ağırlıklı token dağılımınız
- hangi araçların bağlamınıza en çok hacim koyduğu ve ortalama sonuç boyutları
- hangi dosyaları tekrar tekrar okuduğunuz
- hangi dosyaların tek başına bir oturuma hâkim olacak kadar büyük olduğu
- görsel ve ikili veri yükleri — ayrı ve dürüstçe sayılmış

```
  [HIGH] 94 dosya 5+ kez okundu
      Değişmemiş aynı dosyaları yeniden okumak, ilk okumanın ötesinde
      yaklaşık 2,4 milyon token'a mal oldu (yaklaşık). En kötüsü:
      project-notes.md (107 kez).
      -> İçerikleri bağlamda kalıcı olmadığı için yeniden okunuyorlar.

  [HIGH] Bağlama geri dönen her şeyin %50'sini Read üretiyor
      3.100 çağrı toplam ~4,5 milyon token döndürdü; çağrı başına ortalama
      1.400 token, tek seferlik en büyük sonuç ~16.800 token.
      -> Dosyanın tamamı yerine offset/limit ile okuyun.
```

## Siz bir şey yazmadan önce ne yükleniyor

```bash
python burnrate.py --startup
```

Başlangıç bağlamı **her oturumun her turunda** faturalanır; dolayısıyla bilebileceğiniz en yüksek kaldıraçlı bilgidir. Gerçek çıktı:

```
-- ÖLÇÜLEN (her oturumun ilk faturalanan turu) ------------------
  başlangıç bağlamı (medyan)      60.057 token   310 oturumda
  Sonraki HER turda cache_read olarak yeniden gönderilir.

-- ATFEDİLEN (yapılandırmanızdan tarandı, yaklaşık) ------------
  skill açıklamaları                    12.998  105 skill
  CLAUDE.md (kullanıcı)                  3.674
  bellek dizini (MEMORY.md)              2.718  sınır 200 satır / 25 KB
  alt ajan açıklamaları                  1.258  18 ajan
  atfedilen toplam                      20.648

  atfedilemeyen kalan                   39.409  sistem istemi + araç şemaları
  sizin payınız                           %34,4  kesebileceğiniz kısım
```

Bunu bir yapılandırma dosyası tahmincisinden ayıran üç şey var:

- **Ölçülen** sayı kesindir — kelime saymaktan değil, `usage` alanından gelir.
- **Kalan** gizlenmek yerine raporlanır. Bu başlangıç maliyetinin üçte ikisi sistem istemi ve araç şemalarıdır; kendi dosyalarınızı ne kadar düzenlerseniz düzenleyin değişmez. Bunu söylemek, kımıldatamayacağınız bir sayıyı optimize etmenizi önler.
- Skill'ler ve ajanlar için **yalnızca frontmatter sayılır**. Gövdeleri talep üzerine yüklenir; skill dosyalarının tamamını saymak — yapılandırma dizinlerini tarayan araçların sıkça yaptığı gibi — başlangıç maliyetini kat kat abartır.

Alışıldık sürpriz: **kurulu ama kullanılmayan skill'ler `CLAUDE.md`'den ağır basar.** Her skill'in açıklaması, siz çağırsanız da çağırmasanız da her turda yüklenir — bu yüzden `--startup` ayrıca tüm geçmişinizdeki gerçek `Skill` aracı çağrılarını sayar ve *kurulu* olanı *kullanılan*dan ayırır:

```
  TÜM geçmişinizde (416 kayıt, --days penceresi değil):
    kurulu 105  |  çağrı kaydı olan 12  |  olmayan 93

  Tur başına ~10.956 token, çağrı kaydı olmayan skill'lere gidiyor.
  100 turluk bir oturumda bu ~1,1 milyon eder.
```

Bu bir israf tahmini değil — adı sanı belli bir israf, en ağırdan başlayarak sıralanmış. Yalnızca yapılandırma dizininizi tarayan bir araç bunu bilemez.

## Kendi tasarrufunuzu kanıtlayın

```bash
python burnrate.py --snapshot before
#  ... bir şeyler değiştirin ...
python burnrate.py --compare before
```

`--compare` **tur başına ortalamaları** raporlar; böylece daha yoğun bir hafta gerileme kılığına giremez:

```
                                            önce       şimdi     değişim
  cache write (yeni bağlam)                   8.6K       5.9K    -%31,7
  cache read (her tur yeniden gönderilen)    213.3K     219.5K      %2,9
  çıktı (ajanın yazdığı)                       1.4K       1.4K      %1,3

  maliyet ağırlıklı, tur başına                39.1K      36.4K     -%6,9

  Bu sizin ölçülen değişiminizdir. Başkasınınki hakkında bir iddia değildir.
```

## Skill olarak kurun

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Kurulduğunda üç şey yapar: önerilerde bulunmadan önce ölçer; ucuz %0,6 yerine pahalı %83–99'u hedefleyen bir bağlam disiplini uygular; ve iyileşmenin bir iddia değil olgu olması için yeniden ölçer. Etkiye göre sıralanmış, her kesintinin bedelini de belirten tam kesinti kılavuzu [`references/cuts.md`](../../plugins/burnrate/skills/burnrate/references/cuts.md) içinde.

## Yapmayacakları

- **Ajanınızı tuhaf konuşturmaz.** Telgraf üslubu faturanın küçük bir dilimini kırpar ama sonuçları incelemeyi zorlaştırır.
- **Size bir ortalama vermez.** Yalnızca sizin ölçülmüş sayılarınızı.
- **Kendi maliyetini gizlemez.** Çağrıldığında bu dosya da bağlama girer. Kısa oturumlarda bu ek yük, sağladığı tasarrufu aşabilir — ve `--compare` bunu size dürüstçe gösterir.
- **Doğruluğu token'la takas etmez.** Özlük yalnızca iletilen şey için geçerlidir; akıl yürütme, testler ya da kodun ve hataların birebir metni için asla.

## Bilinen sınırlar

- Token toplamları `usage` alanından gelir ve kesindir. Araç sonucu hacmi ~4 karakter/token oranıyla dönüştürülür ve göründüğü her yerde yaklaşık olarak işaretlenir.
- Görseller ve PDF'ler karakter sayısına göre değil boyutlarına göre faturalanır. Ayrı sayılır ve asla token sayısına çevrilmez.
- Maliyet ağırlıklandırması, modele özel fiyatları değil, token sınıfları arasındaki yayımlanmış oranları kullanır — ağırlıklı sütun bir paydır, para tutarı değil.
- Abonelik planları kullanımı API fiyatlandırmasından farklı ağırlıklandırabilir. Bu yüzden hem ham hem ağırlıklı paylar raporlanır; hiçbiri fatura olarak sunulmaz.
- Yalnızca yerel oturum kayıtlarını görür. Başka bir makinede ya da tarayıcıda yapılan iş sayılmaz.
- Yukarıdaki veri kümesi, yoğun kullanan tek bir kişinin 348 oturumudur. Bu bir kanıttır, evrensel bir yasa değil — ki asıl mesele de bu. Kendi verinizle çalıştırın.

## Lisans

MIT
